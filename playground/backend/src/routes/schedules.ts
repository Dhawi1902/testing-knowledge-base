import { Router, Request, Response } from 'express';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { queryDb, queryOne } from '../config/database';
import { authenticate } from '../middleware/auth';
import { validateCsrf, generateCsrfTokens } from '../middleware/csrf';
import { requireAjaxHeaders } from '../middleware/ajax';

export const schedulesRouter = Router();

schedulesRouter.use(requireAjaxHeaders);
schedulesRouter.use(authenticate);

// ============================================================
// Task-scoped schedule routes (mounted at /api/tasks)
// ============================================================

// GET /api/tasks/:id/schedule - Get available slots + form tokens
schedulesRouter.get('/:id/schedule', async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const task = await queryOne<{ id: number; title: string; project_code: string }>(
      'SELECT id, title, project_code FROM tasks WHERE id = $1',
      [taskId]
    );

    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    // Generate available time slots for the next 5 business days
    const availableSlots: Array<{ date: string; times: string[] }> = [];
    const now = new Date();
    let daysAdded = 0;

    for (let i = 1; daysAdded < 5; i++) {
      const date = new Date(now);
      date.setDate(date.getDate() + i);
      const dayOfWeek = date.getDay();

      // Skip weekends
      if (dayOfWeek === 0 || dayOfWeek === 6) continue;

      availableSlots.push({
        date: date.toISOString().split('T')[0],
        times: ['09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00'],
      });
      daysAdded++;
    }

    const csrfTokens = await generateCsrfTokens();

    res.json({
      taskId: task.id,
      taskTitle: task.title,
      projectCode: task.project_code,
      availableSlots,
      departments: ['Engineering', 'Design', 'Marketing', 'Operations', 'Finance'],
      _csrf: csrfTokens._csrf,
      _formId: csrfTokens._formId,
    });
  } catch (err) {
    console.error('Get schedule error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/tasks/:id/schedule - Submit schedule → 302 redirect
schedulesRouter.post('/:id/schedule', validateCsrf, async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const task = await queryOne('SELECT id FROM tasks WHERE id = $1', [taskId]);
    if (!task) {
      res.status(404).json({ error: 'Task not found' });
      return;
    }

    const {
      assigneeId,
      department,
      priority,
      submittedAt,
      scheduledDate,
      scheduledTime,
      projectCode,
      notes,
      // Extra CSV fields JMeter might send:
      contactName,
      contactEmail,
      location,
      duration,
      meetingType,
      roomNumber,
      participants,
    } = req.body;

    if (!scheduledDate || !scheduledTime) {
      res.status(400).json({ error: 'scheduledDate and scheduledTime are required' });
      return;
    }

    const confirmationId = `SCH-${Date.now()}-${uuidv4().substring(0, 8)}`;
    const confirmHash = crypto.createHash('sha256')
      .update(confirmationId + taskId + req.user!.userId)
      .digest('hex');

    // Store everything in the payload JSONB for the heavy payload exercise
    const payload = {
      assigneeId,
      department,
      priority,
      submittedAt,
      scheduledDate,
      scheduledTime,
      projectCode,
      notes,
      contactName,
      contactEmail,
      location,
      duration,
      meetingType,
      roomNumber,
      participants,
      createdBy: req.user!.email,
    };

    await queryOne(
      `INSERT INTO schedules (task_id, user_id, confirmation_id, confirm_hash, slot_date, slot_time, department, priority, notes, payload)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING id`,
      [
        taskId,
        req.user!.userId,
        confirmationId,
        confirmHash,
        scheduledDate,
        scheduledTime,
        department || null,
        priority || null,
        notes || null,
        JSON.stringify(payload),
      ]
    );

    // 302 redirect to review page
    res.redirect(302, `/api/schedules/${confirmationId}/review`);
  } catch (err) {
    console.error('Submit schedule error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/tasks/:id/schedules - List existing schedules for a task
schedulesRouter.get('/:id/schedules', async (req: Request, res: Response) => {
  try {
    const taskId = parseInt(req.params.id);

    const schedules = await queryDb(
      `SELECT s.*, u.display_name as booked_by
       FROM schedules s
       JOIN users u ON s.user_id = u.id
       WHERE s.task_id = $1
       ORDER BY s.created_at DESC`,
      [taskId]
    );

    res.json({ schedules });
  } catch (err) {
    console.error('List schedules error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
