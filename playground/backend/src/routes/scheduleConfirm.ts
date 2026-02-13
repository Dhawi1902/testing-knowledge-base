import { Router, Request, Response } from 'express';
import { queryDb, queryOne } from '../config/database';
import { authenticate } from '../middleware/auth';
import { validateCsrf, generateCsrfTokens } from '../middleware/csrf';
import { requireAjaxHeaders } from '../middleware/ajax';

export const scheduleConfirmRouter = Router();

scheduleConfirmRouter.use(requireAjaxHeaders);
scheduleConfirmRouter.use(authenticate);

// GET /api/schedules/:confirmationId/review - View schedule details
scheduleConfirmRouter.get('/:confirmationId/review', async (req: Request, res: Response) => {
  try {
    const { confirmationId } = req.params;

    const schedule = await queryOne<Record<string, any>>(
      `SELECT s.*, t.title as task_title, u.display_name as booked_by
       FROM schedules s
       JOIN tasks t ON s.task_id = t.id
       JOIN users u ON s.user_id = u.id
       WHERE s.confirmation_id = $1`,
      [confirmationId]
    );

    if (!schedule) {
      res.status(404).json({ error: 'Schedule not found' });
      return;
    }

    const csrfTokens = await generateCsrfTokens();

    res.json({
      ...schedule,
      _csrf: csrfTokens._csrf,
      _formId: csrfTokens._formId,
    });
  } catch (err) {
    console.error('Review schedule error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/schedules/:confirmationId/confirm - Confirm booking
// Returns confirmUrl with raw hash (no key=value — the hash IS the query string)
scheduleConfirmRouter.post('/:confirmationId/confirm', validateCsrf, async (req: Request, res: Response) => {
  try {
    const { confirmationId } = req.params;

    const schedule = await queryOne<{ id: number; status: string; confirm_hash: string }>(
      'SELECT id, status, confirm_hash FROM schedules WHERE confirmation_id = $1',
      [confirmationId]
    );

    if (!schedule) {
      res.status(404).json({ error: 'Schedule not found' });
      return;
    }

    if (schedule.status !== 'pending') {
      res.status(400).json({ error: `Schedule already ${schedule.status}` });
      return;
    }

    await queryDb(
      "UPDATE schedules SET status = 'confirmed' WHERE id = $1",
      [schedule.id]
    );

    // Return confirmUrl with raw hash — no key=value pair
    // The hash itself IS the entire query string: /api/schedules/confirm?<hash>
    res.json({
      message: 'Schedule confirmed',
      confirmationId,
      status: 'confirmed',
      confirmUrl: `/api/schedules/confirm?${schedule.confirm_hash}`,
    });
  } catch (err) {
    console.error('Confirm schedule error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/schedules/confirm?<hash> - One-time confirmation link
// The entire query string after ? is the hash (no key=value)
scheduleConfirmRouter.get('/confirm', async (req: Request, res: Response) => {
  try {
    // Extract the raw query string — everything after ?
    // Express doesn't parse this as a key=value pair
    const rawQuery = req.originalUrl.split('?')[1];

    if (!rawQuery) {
      res.status(400).json({ error: 'Confirmation hash required' });
      return;
    }

    const schedule = await queryOne<Record<string, any>>(
      `SELECT s.*, t.title as task_title, u.display_name as booked_by
       FROM schedules s
       JOIN tasks t ON s.task_id = t.id
       JOIN users u ON s.user_id = u.id
       WHERE s.confirm_hash = $1`,
      [rawQuery]
    );

    if (!schedule) {
      res.status(404).json({ error: 'Invalid confirmation link' });
      return;
    }

    res.json({
      message: 'Schedule verified',
      confirmationId: schedule.confirmation_id,
      taskTitle: schedule.task_title,
      bookedBy: schedule.booked_by,
      date: schedule.slot_date,
      time: schedule.slot_time,
      department: schedule.department,
      status: schedule.status,
    });
  } catch (err) {
    console.error('Confirm link error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
