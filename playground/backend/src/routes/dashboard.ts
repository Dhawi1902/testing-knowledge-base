import { Router, Request, Response } from 'express';
import { queryDb, queryOne } from '../config/database';
import { authenticate } from '../middleware/auth';
import { requireAjaxHeaders } from '../middleware/ajax';

export const dashboardRouter = Router();

dashboardRouter.use(requireAjaxHeaders);
dashboardRouter.use(authenticate);

// GET /api/dashboard/stats - Task counts by status
dashboardRouter.get('/stats', async (req: Request, res: Response) => {
  try {
    let userFilter = '';
    const params: any[] = [];

    // Staff sees only their own stats
    if (req.user!.role === 'staff') {
      params.push(req.user!.userId);
      userFilter = `WHERE creator_id = $1 OR assignee_id = $1`;
    }

    const stats = await queryDb(
      `SELECT status, COUNT(*) as count FROM tasks ${userFilter} GROUP BY status ORDER BY status`,
      params
    );

    const totalResult = await queryOne<{ count: string }>(
      `SELECT COUNT(*) as count FROM tasks ${userFilter}`,
      params
    );

    res.json({
      byStatus: stats,
      total: parseInt(totalResult?.count || '0'),
    });
  } catch (err) {
    console.error('Dashboard stats error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/dashboard/recent - Recent activity feed
dashboardRouter.get('/recent', async (req: Request, res: Response) => {
  try {
    const limit = Math.min(parseInt(req.query.limit as string) || 10, 50);

    // Recent tasks
    const recentTasks = await queryDb(
      `SELECT t.id, t.title, t.status, t.updated_at, u.display_name as assignee_name
       FROM tasks t
       LEFT JOIN users u ON t.assignee_id = u.id
       ORDER BY t.updated_at DESC
       LIMIT $1`,
      [limit]
    );

    // Recent comments
    const recentComments = await queryDb(
      `SELECT c.id, c.content, c.created_at, c.task_id, u.display_name as author_name,
              t.title as task_title
       FROM comments c
       JOIN users u ON c.user_id = u.id
       JOIN tasks t ON c.task_id = t.id
       ORDER BY c.created_at DESC
       LIMIT $1`,
      [limit]
    );

    res.json({
      recentTasks,
      recentComments,
    });
  } catch (err) {
    console.error('Dashboard recent error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
