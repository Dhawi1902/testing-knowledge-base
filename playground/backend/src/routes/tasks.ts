import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import { queryDb, queryOne } from '../config/database';
import { authenticate } from '../middleware/auth';
import { requireRole } from '../middleware/roles';
import { validateCsrf, generateCsrfTokens } from '../middleware/csrf';
import { requireAjaxHeaders } from '../middleware/ajax';

const UPLOAD_DIR = process.env.UPLOAD_DIR || '/app/uploads';

// Ensure upload directory exists
if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOAD_DIR),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${uuidv4()}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10 MB
});

export const tasksRouter = Router();

tasksRouter.use(requireAjaxHeaders);
tasksRouter.use(authenticate);

// GET /api/tasks - List tasks with pagination and filtering
tasksRouter.get('/', async (req: Request, res: Response) => {
  try {
    const page = parseInt(req.query.page as string) || 1;
    const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);
    const offset = (page - 1) * limit;
    const status = req.query.status as string;
    const assignee = req.query.assignee as string;

    let whereClause = '';
    const params: any[] = [];
    const conditions: string[] = [];

    if (status) {
      params.push(status);
      conditions.push(`t.status = $${params.length}`);
    }

    if (assignee) {
      params.push(parseInt(assignee));
      conditions.push(`t.assignee_id = $${params.length}`);
    }

    // Staff can only see their own tasks + tasks assigned to them
    if (req.user!.role === 'staff') {
      params.push(req.user!.userId);
      conditions.push(`(t.creator_id = $${params.length} OR t.assignee_id = $${params.length})`);
    }

    if (conditions.length > 0) {
      whereClause = 'WHERE ' + conditions.join(' AND ');
    }

    // Get total count
    const countResult = await queryOne<{ count: string }>(
      `SELECT COUNT(*) as count FROM tasks t ${whereClause}`,
      params
    );
    const total = parseInt(countResult?.count || '0');

    // Get tasks
    const taskParams = [...params, limit, offset];
    const tasks = await queryDb(
      `SELECT t.id, t.title, t.description, t.status, t.priority, t.project_code,
              t.assignee_id, t.creator_id, t.created_at, t.updated_at,
              u1.display_name as assignee_name,
              u2.display_name as creator_name
       FROM tasks t
       LEFT JOIN users u1 ON t.assignee_id = u1.id
       LEFT JOIN users u2 ON t.creator_id = u2.id
       ${whereClause}
       ORDER BY t.created_at DESC
       LIMIT $${taskParams.length - 1} OFFSET $${taskParams.length}`,
      taskParams
    );

    res.json({
      tasks,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    console.error('List tasks error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/tasks/batch-edit - Load batch edit view (task list + tokens)
// Must be before /:id to avoid parameter match
tasksRouter.get('/batch-edit', async (req: Request, res: Response) => {
  try {
    // Return a page of tasks for batch editing (managers can see all)
    const limit = 20;
    let tasks;

    if (req.user!.role === 'manager' || req.user!.role === 'admin') {
      tasks = await queryDb(
        `SELECT t.id, t.title, t.status, t.priority, t.assignee_id,
                u.display_name as assignee_name
         FROM tasks t
         LEFT JOIN users u ON t.assignee_id = u.id
         ORDER BY t.id ASC
         LIMIT $1`,
        [limit]
      );
    } else {
      tasks = await queryDb(
        `SELECT t.id, t.title, t.status, t.priority, t.assignee_id,
                u.display_name as assignee_name
         FROM tasks t
         LEFT JOIN users u ON t.assignee_id = u.id
         WHERE t.creator_id = $1 OR t.assignee_id = $1
         ORDER BY t.id ASC
         LIMIT $2`,
        [req.user!.userId, limit]
      );
    }

    const csrfTokens = await generateCsrfTokens();

    res.json({
      tasks,
      _csrf: csrfTokens._csrf,
      _formId: csrfTokens._formId,
    });
  } catch (err) {
    console.error('Batch edit error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/tasks/batch-update - Apply batch changes
// changesList is URL-encoded JSON: {"1":{"ID":"42","STS":"in_progress","PRI":"high","ASG":"3"}, ...}
tasksRouter.post('/batch-update', validateCsrf, async (req: Request, res: Response) => {
  try {
    const { changesList } = req.body;

    if (!changesList) {
      res.status(400).json({ error: 'changesList is required' });
      return;
    }

    // changesList can be a string (URL-encoded JSON) or already parsed object
    let changes: Record<string, { ID: string; STS?: string; PRI?: string; ASG?: string }>;
    try {
      changes = typeof changesList === 'string' ? JSON.parse(changesList) : changesList;
    } catch {
      res.status(400).json({ error: 'Invalid changesList format. Must be JSON.' });
      return;
    }

    const results: Array<{ taskId: number; status: string }> = [];
    const errors: Array<{ taskId: string; error: string }> = [];

    const validStatuses = ['open', 'in_progress', 'completed', 'pending_review', 'approved', 'rejected'];
    const validPriorities = ['low', 'medium', 'high', 'urgent'];

    for (const [_rowKey, change] of Object.entries(changes)) {
      const taskId = parseInt(change.ID);
      if (isNaN(taskId)) {
        errors.push({ taskId: change.ID, error: 'Invalid task ID' });
        continue;
      }

      // Build SET clause dynamically
      const setClauses: string[] = [];
      const params: any[] = [];

      if (change.STS && validStatuses.includes(change.STS)) {
        params.push(change.STS);
        setClauses.push(`status = $${params.length}`);
      }
      if (change.PRI && validPriorities.includes(change.PRI)) {
        params.push(change.PRI);
        setClauses.push(`priority = $${params.length}`);
      }
      if (change.ASG) {
        params.push(parseInt(change.ASG));
        setClauses.push(`assignee_id = $${params.length}`);
      }

      if (setClauses.length === 0) {
        errors.push({ taskId: change.ID, error: 'No valid fields to update' });
        continue;
      }

      setClauses.push('updated_at = NOW()');
      params.push(taskId);

      try {
        await queryDb(
          `UPDATE tasks SET ${setClauses.join(', ')} WHERE id = $${params.length}`,
          params
        );
        results.push({ taskId, status: 'updated' });
      } catch (err: any) {
        errors.push({ taskId: change.ID, error: err.message });
      }
    }

    res.json({
      message: `Batch update completed: ${results.length} updated, ${errors.length} errors`,
      updated: results,
      errors,
    });
  } catch (err) {
    console.error('Batch update error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/tasks/report - Slow endpoint (configurable delay via ?delay=ms)
// Must be before /:id to avoid parameter match
tasksRouter.get('/report', async (req: Request, res: Response) => {
  try {
    const delay = Math.min(parseInt(req.query.delay as string) || 1000, 10000); // Max 10s

    // Simulate slow query
    await new Promise(resolve => setTimeout(resolve, delay));

    const tasks = await queryDb(
      `SELECT t.id, t.title, t.status, t.priority, COUNT(c.id) as comment_count
       FROM tasks t
       LEFT JOIN comments c ON t.id = c.task_id
       GROUP BY t.id
       ORDER BY t.created_at DESC
       LIMIT 50`
    );

    res.json({
      generatedAt: new Date().toISOString(),
      delayMs: delay,
      taskCount: tasks.length,
      tasks,
    });
  } catch (err) {
    console.error('Report error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/tasks/export - Flaky endpoint (random 500 ~20% of the time)
tasksRouter.get('/export', async (req: Request, res: Response) => {
  try {
    // 20% chance of failure
    if (Math.random() < 0.2) {
      res.status(500).json({
        error: 'Export service temporarily unavailable',
        retryAfter: 5,
      });
      return;
    }

    const tasks = await queryDb(
      `SELECT t.*, u1.display_name as assignee_name, u2.display_name as creator_name
       FROM tasks t
       LEFT JOIN users u1 ON t.assignee_id = u1.id
       LEFT JOIN users u2 ON t.creator_id = u2.id
       ORDER BY t.id ASC`
    );

    res.json({
      exportedAt: new Date().toISOString(),
      count: tasks.length,
      tasks,
    });
  } catch (err) {
    console.error('Export error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/tasks/:id - Get task detail with comments
tasksRouter.get('/:id', async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const task = await queryOne(
      `SELECT t.*, u1.display_name as assignee_name, u2.display_name as creator_name
       FROM tasks t
       LEFT JOIN users u1 ON t.assignee_id = u1.id
       LEFT JOIN users u2 ON t.creator_id = u2.id
       WHERE t.id = $1`,
      [taskId]
    );

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    const comments = await queryDb(
      `SELECT c.id, c.content, c.created_at, u.display_name as author_name, u.id as author_id
       FROM comments c
       JOIN users u ON c.user_id = u.id
       WHERE c.task_id = $1
       ORDER BY c.created_at ASC`,
      [taskId]
    );

    // Generate CSRF tokens for forms on this page
    const csrfTokens = await generateCsrfTokens();

    res.json({
      ...task,
      comments,
      _csrf: csrfTokens._csrf,
      _formId: csrfTokens._formId,
    });
  } catch (err) {
    console.error('Get task error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/tasks - Create task
tasksRouter.post('/', validateCsrf, async (req: Request, res: Response) => {
  try {
    const { title, description, priority, assigneeId, projectCode } = req.body;

    if (!title) {
      res.status(400).json({ error: 'Title is required' });
      return;
    }

    const task = await queryOne(
      `INSERT INTO tasks (title, description, status, priority, assignee_id, creator_id, project_code)
       VALUES ($1, $2, 'open', $3, $4, $5, $6)
       RETURNING *`,
      [title, description || null, priority || 'medium', assigneeId || null, req.user!.userId, projectCode || null]
    );

    res.status(201).json(task);
  } catch (err) {
    console.error('Create task error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/tasks/:id - Update task
tasksRouter.put('/:id', validateCsrf, async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);
    const { title, description, status, priority, assigneeId } = req.body;

    // Check task exists
    const existing = await queryOne<{ creator_id: number }>(
      'SELECT creator_id FROM tasks WHERE id = $1',
      [taskId]
    );

    if (!existing) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    // Staff can only update their own tasks
    if (req.user!.role === 'staff' && existing.creator_id !== req.user!.userId) {
      res.status(403).json({ error: 'You can only update your own tasks' });
      return;
    }

    const task = await queryOne(
      `UPDATE tasks SET
        title = COALESCE($1, title),
        description = COALESCE($2, description),
        status = COALESCE($3, status),
        priority = COALESCE($4, priority),
        assignee_id = COALESCE($5, assignee_id),
        updated_at = NOW()
       WHERE id = $6
       RETURNING *`,
      [title, description, status, priority, assigneeId, taskId]
    );

    res.json(task);
  } catch (err) {
    console.error('Update task error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /api/tasks/:id - Delete task
tasksRouter.delete('/:id', validateCsrf, async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const existing = await queryOne<{ creator_id: number }>(
      'SELECT creator_id FROM tasks WHERE id = $1',
      [taskId]
    );

    if (!existing) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    // Staff can only delete their own tasks
    if (req.user!.role === 'staff' && existing.creator_id !== req.user!.userId) {
      res.status(403).json({ error: 'You can only delete your own tasks' });
      return;
    }

    await queryDb('DELETE FROM tasks WHERE id = $1', [taskId]);
    res.json({ message: 'Task deleted' });
  } catch (err) {
    console.error('Delete task error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/tasks/:id/attachments - Upload file attachment
// multer parses multipart/form-data BEFORE validateCsrf reads req.body
tasksRouter.post(
  '/:id/attachments',
  upload.single('file'),
  validateCsrf,
  async (req: Request, res: Response) => {
    try {
      const taskId = parseInt(req.params.id);

      const task = await queryOne('SELECT id FROM tasks WHERE id = $1', [taskId]);
      if (!task) {
        res.status(404).json({ error: 'Task not found' });
        return;
      }

      if (!req.file) {
        res.status(400).json({ error: 'No file uploaded. Send as multipart field named "file"' });
        return;
      }

      const attachment = await queryOne<{ id: number }>(
        `INSERT INTO attachments (task_id, user_id, original_name, stored_name, mime_type, size_bytes)
         VALUES ($1, $2, $3, $4, $5, $6)
         RETURNING *`,
        [taskId, req.user!.userId, req.file.originalname, req.file.filename, req.file.mimetype, req.file.size]
      );

      res.status(201).json({
        ...attachment,
        downloadUrl: `/api/files/${attachment!.id}/${encodeURIComponent(req.file.originalname)}`,
      });
    } catch (err) {
      console.error('Upload error:', err);
      res.status(500).json({ error: 'Internal server error' });
    }
  }
);

// GET /api/tasks/:id/attachments - List attachments for a task
tasksRouter.get('/:id/attachments', async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const attachments = await queryDb(
      `SELECT a.*, u.display_name as uploader_name
       FROM attachments a
       JOIN users u ON a.user_id = u.id
       WHERE a.task_id = $1
       ORDER BY a.created_at DESC`,
      [taskId]
    );

    res.json({
      attachments: attachments.map((a: any) => ({
        ...a,
        downloadUrl: `/api/files/${a.id}/${encodeURIComponent(a.original_name)}`,
      })),
    });
  } catch (err) {
    console.error('List attachments error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/tasks/:id/comments - Add comment to task
tasksRouter.post('/:id/comments', validateCsrf, async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);
    const { content } = req.body;

    if (!content) {
      res.status(400).json({ error: 'Comment content is required' });
      return;
    }

    const task = await queryOne('SELECT id FROM tasks WHERE id = $1', [taskId]);
    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    const comment = await queryOne(
      `INSERT INTO comments (task_id, user_id, content)
       VALUES ($1, $2, $3)
       RETURNING *`,
      [taskId, req.user!.userId, content]
    );

    res.status(201).json(comment);
  } catch (err) {
    console.error('Add comment error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/tasks/:id/submit-review - Submit task for review (staff → pending_review)
tasksRouter.put('/:id/submit-review', validateCsrf, async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const existing = await queryOne<{ status: string; creator_id: number }>(
      'SELECT status, creator_id FROM tasks WHERE id = $1',
      [taskId]
    );

    if (!existing) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    // Only the creator (or assignee) can submit for review
    if (req.user!.role === 'staff' && existing.creator_id !== req.user!.userId) {
      res.status(403).json({ error: 'Only the task creator can submit for review' });
      return;
    }

    // Can only submit from open or in_progress or rejected
    if (!['open', 'in_progress', 'rejected'].includes(existing.status)) {
      res.status(400).json({ error: `Cannot submit for review from status "${existing.status}"` });
      return;
    }

    const task = await queryOne(
      `UPDATE tasks SET status = 'pending_review', updated_at = NOW()
       WHERE id = $1 RETURNING *`,
      [taskId]
    );

    res.json(task);
  } catch (err) {
    console.error('Submit for review error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/tasks/:id/approve - Approve task (manager only → approved)
tasksRouter.put('/:id/approve', requireRole('manager', 'admin'), validateCsrf, async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const existing = await queryOne<{ status: string }>(
      'SELECT status FROM tasks WHERE id = $1',
      [taskId]
    );

    if (!existing) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    if (existing.status !== 'pending_review') {
      res.status(400).json({ error: `Cannot approve task with status "${existing.status}". Must be "pending_review"` });
      return;
    }

    const task = await queryOne(
      `UPDATE tasks SET status = 'approved', updated_at = NOW()
       WHERE id = $1 RETURNING *`,
      [taskId]
    );

    // Add approval comment if remarks provided
    if (req.body.remarks) {
      await queryOne(
        `INSERT INTO comments (task_id, user_id, content) VALUES ($1, $2, $3) RETURNING *`,
        [taskId, req.user!.userId, `Approved: ${req.body.remarks}`]
      );
    }

    res.json(task);
  } catch (err) {
    console.error('Approve task error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/tasks/:id/reject - Reject task with remarks (manager only → rejected)
tasksRouter.put('/:id/reject', requireRole('manager', 'admin'), validateCsrf, async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);
    const { remarks } = req.body;

    if (!remarks) {
      res.status(400).json({ error: 'Remarks are required when rejecting a task' });
      return;
    }

    const existing = await queryOne<{ status: string }>(
      'SELECT status FROM tasks WHERE id = $1',
      [taskId]
    );

    if (!existing) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    if (existing.status !== 'pending_review') {
      res.status(400).json({ error: `Cannot reject task with status "${existing.status}". Must be "pending_review"` });
      return;
    }

    const task = await queryOne(
      `UPDATE tasks SET status = 'rejected', updated_at = NOW()
       WHERE id = $1 RETURNING *`,
      [taskId]
    );

    // Add rejection comment
    await queryOne(
      `INSERT INTO comments (task_id, user_id, content) VALUES ($1, $2, $3) RETURNING *`,
      [taskId, req.user!.userId, `Rejected: ${remarks}`]
    );

    res.json(task);
  } catch (err) {
    console.error('Reject task error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
