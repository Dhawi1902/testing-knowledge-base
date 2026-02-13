import { Router, Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { pool, queryDb, queryOne } from '../config/database';
import { redisClient } from '../config/redis';
import { generateCsrfTokens, validateCsrf } from '../middleware/csrf';
import { verifyPassword } from '../services/auth';
import { reseedDatabase } from '../seed/seed';

export const adminRouter = Router();

const SESSION_PREFIX = 'admin_session:';
const SESSION_TTL = 60 * 60; // 1 hour

// Middleware to verify admin session cookie
async function requireAdminSession(req: Request, res: Response, next: NextFunction): Promise<void> {
  const sessionId = req.cookies?.SESSIONID;

  if (!sessionId) {
    res.status(401).json({ error: 'Admin session required. Please login at /admin/login' });
    return;
  }

  const userId = await redisClient.get(`${SESSION_PREFIX}${sessionId}`);
  if (!userId) {
    res.status(401).json({ error: 'Session expired. Please login again.' });
    return;
  }

  const user = await queryOne<{ id: number; role: string; display_name: string }>(
    'SELECT id, role, display_name FROM users WHERE id = $1',
    [parseInt(userId)]
  );

  if (!user || user.role !== 'admin') {
    res.status(403).json({ error: 'Admin access required' });
    return;
  }

  (req as any).adminUser = user;
  next();
}

// Note: health and seed routes skip AJAX header enforcement (curl-friendly)

// GET /api/admin/health - Health check
adminRouter.get('/health', async (_req: Request, res: Response) => {
  try {
    await pool.query('SELECT 1');
    await redisClient.ping();

    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      services: {
        database: 'connected',
        redis: 'connected',
      },
    });
  } catch (err) {
    console.error('Health check failed:', err);
    res.status(503).json({
      status: 'error',
      timestamp: new Date().toISOString(),
      error: (err as Error).message,
    });
  }
});

// POST /api/admin/seed - Reset database to seeded state
adminRouter.post('/seed', async (_req: Request, res: Response) => {
  try {
    await reseedDatabase();
    await redisClient.flushDb();

    res.json({
      status: 'ok',
      message: 'Database re-seeded successfully',
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    console.error('Seed error:', err);
    res.status(500).json({
      error: 'Failed to re-seed database',
      details: (err as Error).message,
    });
  }
});

// GET /admin/login - Admin login page (returns Set-Cookie: SESSIONID + _csrf)
// Note: This is mounted at /admin/login in index.ts, not /api/admin/login
adminRouter.get('/login', async (_req: Request, res: Response) => {
  try {
    // Generate a preliminary session ID (pre-auth, for CSRF linkage)
    const sessionId = uuidv4();
    const csrfTokens = await generateCsrfTokens();

    // Set session cookie
    res.cookie('SESSIONID', sessionId, {
      httpOnly: true,
      sameSite: 'lax',
      maxAge: SESSION_TTL * 1000,
      path: '/',
    });

    // Store the pre-auth session in Redis
    await redisClient.setEx(`${SESSION_PREFIX}preauth:${sessionId}`, SESSION_TTL, 'pending');

    res.json({
      message: 'Admin login page',
      _csrf: csrfTokens._csrf,
      _formId: csrfTokens._formId,
    });
  } catch (err) {
    console.error('Admin login page error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/admin/auth/login - Admin login (cookie session)
adminRouter.post('/auth/login', validateCsrf, async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      res.status(400).json({ error: 'Email and password are required' });
      return;
    }

    const user = await queryOne<{
      id: number;
      email: string;
      password_hash: string;
      display_name: string;
      role: string;
    }>('SELECT id, email, password_hash, display_name, role FROM users WHERE email = $1', [email]);

    if (!user) {
      res.status(401).json({ error: 'Invalid credentials' });
      return;
    }

    const isValid = await verifyPassword(password, user.password_hash);
    if (!isValid) {
      res.status(401).json({ error: 'Invalid credentials' });
      return;
    }

    if (user.role !== 'admin') {
      res.status(403).json({ error: 'Admin access required' });
      return;
    }

    // Create authenticated session
    const sessionId = uuidv4();
    await redisClient.setEx(`${SESSION_PREFIX}${sessionId}`, SESSION_TTL, String(user.id));

    // Store in DB for tracking
    const expiresAt = new Date(Date.now() + SESSION_TTL * 1000);
    await queryDb(
      'INSERT INTO admin_sessions (session_id, user_id, expires_at) VALUES ($1, $2, $3)',
      [sessionId, user.id, expiresAt]
    );

    // Set session cookie
    res.cookie('SESSIONID', sessionId, {
      httpOnly: true,
      sameSite: 'lax',
      maxAge: SESSION_TTL * 1000,
      path: '/',
    });

    res.json({
      message: 'Admin login successful',
      user: {
        id: user.id,
        email: user.email,
        displayName: user.display_name,
        role: user.role,
      },
    });
  } catch (err) {
    console.error('Admin auth error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/admin/auth/logout - Invalidate admin session
adminRouter.post('/auth/logout', async (req: Request, res: Response) => {
  try {
    const sessionId = req.cookies?.SESSIONID;

    if (sessionId) {
      await redisClient.del(`${SESSION_PREFIX}${sessionId}`);
      await queryDb('DELETE FROM admin_sessions WHERE session_id = $1', [sessionId]);
    }

    res.clearCookie('SESSIONID', { path: '/' });
    res.json({ message: 'Logged out successfully' });
  } catch (err) {
    console.error('Admin logout error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/admin/users - List all users (requires admin session)
adminRouter.get('/users', requireAdminSession, async (_req: Request, res: Response) => {
  try {
    const users = await queryDb(
      'SELECT id, email, display_name, role, is_verified, created_at FROM users ORDER BY id'
    );
    res.json({ users, count: users.length });
  } catch (err) {
    console.error('Admin list users error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/admin/stats - System-wide stats (requires admin session)
adminRouter.get('/stats', requireAdminSession, async (_req: Request, res: Response) => {
  try {
    const userCount = await queryOne<{ count: string }>('SELECT COUNT(*) as count FROM users');
    const taskCount = await queryOne<{ count: string }>('SELECT COUNT(*) as count FROM tasks');
    const commentCount = await queryOne<{ count: string }>('SELECT COUNT(*) as count FROM comments');
    const byStatus = await queryDb('SELECT status, COUNT(*) as count FROM tasks GROUP BY status ORDER BY status');
    const byRole = await queryDb('SELECT role, COUNT(*) as count FROM users GROUP BY role ORDER BY role');

    res.json({
      users: parseInt(userCount?.count || '0'),
      tasks: parseInt(taskCount?.count || '0'),
      comments: parseInt(commentCount?.count || '0'),
      tasksByStatus: byStatus,
      usersByRole: byRole,
    });
  } catch (err) {
    console.error('Admin stats error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
