import { Router, Request, Response } from 'express';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { queryOne, queryDb } from '../config/database';
import { generateCsrfTokens, validateCsrf } from '../middleware/csrf';
import { authenticate } from '../middleware/auth';
import { requireAjaxHeaders } from '../middleware/ajax';
import { rateLimit } from '../middleware/rateLimit';
import {
  verifyPassword,
  hashPassword,
  generateAccessToken,
  generateRefreshToken,
  storeRefreshToken,
  validateRefreshToken,
  revokeRefreshToken,
} from '../services/auth';

export const authRouter = Router();

authRouter.use(requireAjaxHeaders);

// GET /api/auth/csrf - Get CSRF tokens for forms
authRouter.get('/csrf', async (_req: Request, res: Response) => {
  try {
    const tokens = await generateCsrfTokens();
    res.json(tokens);
  } catch (err) {
    console.error('CSRF generation error:', err);
    res.status(500).json({ error: 'Failed to generate CSRF tokens' });
  }
});

// POST /api/auth/login - Login with email/password + CSRF
// Rate limited: 10 requests per minute per IP
authRouter.post('/login', rateLimit(10, 60 * 1000), validateCsrf, async (req: Request, res: Response) => {
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
      is_verified: boolean;
    }>('SELECT id, email, password_hash, display_name, role, is_verified FROM users WHERE email = $1', [email]);

    if (!user) {
      res.status(401).json({ error: 'Invalid email or password' });
      return;
    }

    const isValid = await verifyPassword(password, user.password_hash);
    if (!isValid) {
      res.status(401).json({ error: 'Invalid email or password' });
      return;
    }

    // Generate tokens
    const accessToken = generateAccessToken({
      userId: user.id,
      email: user.email,
      role: user.role,
    });
    const refreshToken = generateRefreshToken();
    await storeRefreshToken(user.id, refreshToken);

    res.json({
      accessToken,
      refreshToken,
      user: {
        id: user.id,
        email: user.email,
        displayName: user.display_name,
        role: user.role,
      },
    });
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/auth/register - Register new user + CSRF
// Returns verificationUrl with token and hash for JMeter extraction practice
authRouter.post('/register', validateCsrf, async (req: Request, res: Response) => {
  try {
    const { email, password, displayName } = req.body;

    if (!email || !password || !displayName) {
      res.status(400).json({ error: 'Email, password, and display name are required' });
      return;
    }

    const existing = await queryOne('SELECT id FROM users WHERE email = $1', [email]);
    if (existing) {
      res.status(409).json({ error: 'Email already registered' });
      return;
    }

    const passwordHash = await hashPassword(password);
    const user = await queryOne<{ id: number }>(
      'INSERT INTO users (email, password_hash, display_name, role, is_verified) VALUES ($1, $2, $3, $4, false) RETURNING id',
      [email, passwordHash, displayName, 'staff']
    );

    // Generate verification token and hash
    const token = uuidv4();
    const hash = crypto.createHash('sha256').update(token + user!.id).digest('hex');
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24h

    await queryDb(
      'INSERT INTO verification_tokens (user_id, token, type, expires_at) VALUES ($1, $2, $3, $4)',
      [user!.id, token, 'email_verify', expiresAt]
    );

    res.status(201).json({
      message: 'Registration successful. Please verify your email.',
      userId: user!.id,
      verificationUrl: `/api/auth/verify?token=${token}&hash=${hash}`,
    });
  } catch (err) {
    console.error('Registration error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/auth/verify - Verify email → 302 redirect to /login?verified=true
authRouter.get('/verify', async (req: Request, res: Response) => {
  try {
    const { token, hash } = req.query;

    if (!token || !hash) {
      res.status(400).json({ error: 'Token and hash are required' });
      return;
    }

    const record = await queryOne<{ id: number; user_id: number; used: boolean; expires_at: string }>(
      'SELECT id, user_id, used, expires_at FROM verification_tokens WHERE token = $1 AND type = $2',
      [token, 'email_verify']
    );

    if (!record) {
      res.status(400).json({ error: 'Invalid verification token' });
      return;
    }

    if (record.used) {
      res.status(400).json({ error: 'Token already used' });
      return;
    }

    if (new Date(record.expires_at) < new Date()) {
      res.status(400).json({ error: 'Token expired' });
      return;
    }

    // Verify hash
    const expectedHash = crypto.createHash('sha256').update(token + String(record.user_id)).digest('hex');
    if (hash !== expectedHash) {
      res.status(400).json({ error: 'Invalid hash' });
      return;
    }

    // Mark user as verified
    await queryDb('UPDATE users SET is_verified = true, updated_at = NOW() WHERE id = $1', [record.user_id]);
    await queryDb('UPDATE verification_tokens SET used = true WHERE id = $1', [record.id]);

    res.redirect(302, '/login?verified=true');
  } catch (err) {
    console.error('Verification error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/auth/forgot-password - Request password reset
// Returns resetUrl with hash and expires for JMeter extraction
authRouter.post('/forgot-password', validateCsrf, async (req: Request, res: Response) => {
  try {
    const { email } = req.body;

    if (!email) {
      res.status(400).json({ error: 'Email is required' });
      return;
    }

    const user = await queryOne<{ id: number }>('SELECT id FROM users WHERE email = $1', [email]);
    if (!user) {
      // Don't reveal if email exists
      res.json({ message: 'If that email is registered, a reset link has been sent.' });
      return;
    }

    const token = uuidv4();
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000); // 1h
    const expires = expiresAt.getTime();

    await queryDb(
      'INSERT INTO verification_tokens (user_id, token, type, expires_at) VALUES ($1, $2, $3, $4)',
      [user.id, token, 'password_reset', expiresAt]
    );

    // Hash for URL = SHA256(token + expires)
    const hash = crypto.createHash('sha256').update(token + expires).digest('hex');

    res.json({
      message: 'If that email is registered, a reset link has been sent.',
      resetUrl: `/api/auth/reset-password?hash=${hash}&expires=${expires}`,
      _resetToken: token,
    });
  } catch (err) {
    console.error('Forgot password error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/auth/reset-password - Validate reset link, return form tokens
authRouter.get('/reset-password', async (req: Request, res: Response) => {
  try {
    const { hash, expires } = req.query;

    if (!hash || !expires) {
      res.status(400).json({ error: 'Hash and expires are required' });
      return;
    }

    const expiresMs = parseInt(expires as string);
    if (isNaN(expiresMs) || Date.now() > expiresMs) {
      res.status(400).json({ error: 'Reset link has expired' });
      return;
    }

    // Find matching token by checking hash against all valid password_reset tokens
    const tokens = await queryDb<{ id: number; token: string; user_id: number }>(
      'SELECT id, token, user_id FROM verification_tokens WHERE type = $1 AND expires_at > NOW() AND used = false',
      ['password_reset']
    );

    const matchingToken = tokens.find(t => {
      const expectedHash = crypto.createHash('sha256').update(t.token + expires).digest('hex');
      return expectedHash === hash;
    });

    if (!matchingToken) {
      res.status(400).json({ error: 'Invalid or expired reset link' });
      return;
    }

    const csrfTokens = await generateCsrfTokens();

    res.json({
      valid: true,
      resetToken: matchingToken.token,
      _csrf: csrfTokens._csrf,
      _formId: csrfTokens._formId,
    });
  } catch (err) {
    console.error('Reset password GET error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/auth/reset-password - Submit new password → 302 redirect
authRouter.post('/reset-password', validateCsrf, async (req: Request, res: Response) => {
  try {
    const { resetToken, newPassword } = req.body;

    if (!resetToken || !newPassword) {
      res.status(400).json({ error: 'Reset token and new password are required' });
      return;
    }

    const record = await queryOne<{ id: number; user_id: number; used: boolean }>(
      'SELECT id, user_id, used FROM verification_tokens WHERE token = $1 AND type = $2 AND expires_at > NOW()',
      [resetToken, 'password_reset']
    );

    if (!record || record.used) {
      res.status(400).json({ error: 'Invalid or expired reset token' });
      return;
    }

    const passwordHash = await hashPassword(newPassword);
    await queryDb('UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2', [passwordHash, record.user_id]);
    await queryDb('UPDATE verification_tokens SET used = true WHERE id = $1', [record.id]);

    res.redirect(302, '/login?reset=success');
  } catch (err) {
    console.error('Reset password POST error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/auth/refresh - Refresh access token
authRouter.post('/refresh', async (req: Request, res: Response) => {
  try {
    const { refreshToken } = req.body;

    if (!refreshToken) {
      res.status(400).json({ error: 'Refresh token required' });
      return;
    }

    const tokenData = await validateRefreshToken(refreshToken);
    if (!tokenData) {
      res.status(401).json({ error: 'Invalid or expired refresh token' });
      return;
    }

    const user = await queryOne<{ id: number; email: string; role: string }>(
      'SELECT id, email, role FROM users WHERE id = $1',
      [tokenData.userId]
    );

    if (!user) {
      res.status(401).json({ error: 'User not found' });
      return;
    }

    await revokeRefreshToken(refreshToken);
    const newAccessToken = generateAccessToken({
      userId: user.id,
      email: user.email,
      role: user.role,
    });
    const newRefreshToken = generateRefreshToken();
    await storeRefreshToken(user.id, newRefreshToken);

    res.json({
      accessToken: newAccessToken,
      refreshToken: newRefreshToken,
    });
  } catch (err) {
    console.error('Refresh error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/auth/logout - Revoke refresh token
authRouter.post('/logout', authenticate, async (req: Request, res: Response) => {
  try {
    const { refreshToken } = req.body;

    if (refreshToken) {
      await revokeRefreshToken(refreshToken);
    }

    res.json({ message: 'Logged out successfully' });
  } catch (err) {
    console.error('Logout error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
