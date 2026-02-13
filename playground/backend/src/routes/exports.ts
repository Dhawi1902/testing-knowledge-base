import { Router, Request, Response } from 'express';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { queryDb, queryOne } from '../config/database';
import { authenticate } from '../middleware/auth';
import { requireAjaxHeaders } from '../middleware/ajax';

export const exportsRouter = Router();

exportsRouter.use(requireAjaxHeaders);
exportsRouter.use(authenticate);

// POST /api/exports - Submit export job → 202 Accepted
exportsRouter.post('/', async (req: Request, res: Response) => {
  try {
    const { status, priority, projectCode } = req.body;
    const jobId = `export-${uuidv4().substring(0, 8)}`;
    const totalSteps = 5;

    const filters = { status, priority, projectCode };

    await queryOne(
      `INSERT INTO export_jobs (user_id, job_id, status, total_steps, current_step, filters)
       VALUES ($1, $2, 'processing', $3, 0, $4)
       RETURNING id`,
      [req.user!.userId, jobId, totalSteps, JSON.stringify(filters)]
    );

    // Start async processing (simulate with setTimeout)
    processExportJob(jobId, totalSteps);

    res.status(202).json({
      jobId,
      statusUrl: `/api/exports/${jobId}/status`,
      message: 'Export job submitted. Poll the statusUrl for progress.',
    });
  } catch (err) {
    console.error('Submit export error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/exports/:jobId/status - Poll for progress
// Returns text/html (NOT JSON) — this is the key JMeter challenge
// During processing: <OK>2/5
// When done: <OK>@LNK/api/exports/download/<hash>
exportsRouter.get('/:jobId/status', async (req: Request, res: Response) => {
  try {
    const { jobId } = req.params;

    const job = await queryOne<{
      status: string;
      current_step: number;
      total_steps: number;
      download_hash: string | null;
    }>(
      'SELECT status, current_step, total_steps, download_hash FROM export_jobs WHERE job_id = $1',
      [jobId]
    );

    if (!job) {
      res.status(404).type('text/html').send('<ERR>Job not found');
      return;
    }

    if (job.status === 'failed') {
      res.type('text/html').send('<ERR>Export failed');
      return;
    }

    if (job.status === 'completed' && job.download_hash) {
      // Done — send @LNK response
      res.type('text/html').send(`<OK>@LNK/api/exports/download/${job.download_hash}`);
      return;
    }

    // Still processing
    res.type('text/html').send(`<OK>${job.current_step}/${job.total_steps}`);
  } catch (err) {
    console.error('Export status error:', err);
    res.status(500).type('text/html').send('<ERR>Internal error');
  }
});

// GET /api/exports/download/:hash - Download export result
exportsRouter.get('/download/:hash', async (req: Request, res: Response) => {
  try {
    const { hash } = req.params;

    const job = await queryOne<{ job_id: string; filters: any; completed_at: string }>(
      'SELECT job_id, filters, completed_at FROM export_jobs WHERE download_hash = $1 AND status = $2',
      [hash, 'completed']
    );

    if (!job) {
      res.status(404).json({ error: 'Export not found or not ready' });
      return;
    }

    // Generate the export data (simulated report)
    const tasks = await queryDb(
      `SELECT t.id, t.title, t.status, t.priority, t.project_code,
              u1.display_name as assignee_name, u2.display_name as creator_name
       FROM tasks t
       LEFT JOIN users u1 ON t.assignee_id = u1.id
       LEFT JOIN users u2 ON t.creator_id = u2.id
       ORDER BY t.id ASC`
    );

    res.json({
      jobId: job.job_id,
      exportedAt: job.completed_at,
      filters: job.filters,
      totalRecords: tasks.length,
      data: tasks,
    });
  } catch (err) {
    console.error('Export download error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Simulate async export processing
// Each step takes ~2 seconds, then marks as completed with a download hash
async function processExportJob(jobId: string, totalSteps: number) {
  for (let step = 1; step <= totalSteps; step++) {
    await new Promise(resolve => setTimeout(resolve, 2000));

    if (step < totalSteps) {
      await queryDb(
        'UPDATE export_jobs SET current_step = $1 WHERE job_id = $2',
        [step, jobId]
      );
    } else {
      // Final step — generate download hash and mark as completed
      const downloadHash = crypto.randomBytes(32).toString('base64url');
      await queryDb(
        `UPDATE export_jobs SET current_step = $1, status = 'completed', download_hash = $2, completed_at = NOW()
         WHERE job_id = $3`,
        [step, downloadHash, jobId]
      );
    }
  }
}
