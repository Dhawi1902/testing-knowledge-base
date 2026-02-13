import { Router, Request, Response } from 'express';
import { queryDb } from '../config/database';
import { authenticate } from '../middleware/auth';
import { requireAjaxHeaders } from '../middleware/ajax';

export const reportsRouter = Router();

reportsRouter.use(requireAjaxHeaders);
reportsRouter.use(authenticate);

// GET /api/reports/full-export - Memory-intensive large export
// Returns all tasks with all comments and attachments
reportsRouter.get('/full-export', async (_req: Request, res: Response) => {
  try {
    // Simulate a memory-intensive operation with joined data
    const tasks = await queryDb(
      `SELECT t.*, u1.display_name as assignee_name, u2.display_name as creator_name
       FROM tasks t
       LEFT JOIN users u1 ON t.assignee_id = u1.id
       LEFT JOIN users u2 ON t.creator_id = u2.id
       ORDER BY t.id ASC`
    );

    // Load all comments for all tasks
    const comments = await queryDb(
      `SELECT c.*, u.display_name as author_name
       FROM comments c
       JOIN users u ON c.user_id = u.id
       ORDER BY c.task_id ASC, c.created_at ASC`
    );

    // Load all attachments
    const attachments = await queryDb(
      `SELECT a.*, u.display_name as uploader_name
       FROM attachments a
       JOIN users u ON a.user_id = u.id
       ORDER BY a.task_id ASC`
    );

    // Group comments and attachments by task
    const commentsByTask: Record<number, any[]> = {};
    for (const c of comments) {
      const tid = (c as any).task_id;
      if (!commentsByTask[tid]) commentsByTask[tid] = [];
      commentsByTask[tid].push(c);
    }

    const attachmentsByTask: Record<number, any[]> = {};
    for (const a of attachments) {
      const tid = (a as any).task_id;
      if (!attachmentsByTask[tid]) attachmentsByTask[tid] = [];
      attachmentsByTask[tid].push(a);
    }

    // Build full export
    const fullExport = tasks.map((t: any) => ({
      ...t,
      comments: commentsByTask[t.id] || [],
      attachments: attachmentsByTask[t.id] || [],
    }));

    res.json({
      exportedAt: new Date().toISOString(),
      totalTasks: fullExport.length,
      totalComments: comments.length,
      totalAttachments: attachments.length,
      tasks: fullExport,
    });
  } catch (err) {
    console.error('Full export error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
