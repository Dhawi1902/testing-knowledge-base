import { Router, Request, Response } from 'express';
import path from 'path';
import fs from 'fs';
import { queryOne } from '../config/database';
import { authenticate } from '../middleware/auth';

const UPLOAD_DIR = process.env.UPLOAD_DIR || '/app/uploads';

export const filesRouter = Router();

// GET /api/files/:fileId/:fileName - Download file
filesRouter.get('/:fileId/:fileName', authenticate, async (req: Request, res: Response) => {
  try {
    const fileId = parseInt(req.params.fileId);

    const attachment = await queryOne<{
      stored_name: string;
      original_name: string;
      mime_type: string;
    }>('SELECT stored_name, original_name, mime_type FROM attachments WHERE id = $1', [fileId]);

    if (!attachment) {
      res.status(404).json({ error: 'File not found' });
      return;
    }

    const filePath = path.join(UPLOAD_DIR, attachment.stored_name);

    if (!fs.existsSync(filePath)) {
      res.status(404).json({ error: 'File not found on disk' });
      return;
    }

    res.setHeader('Content-Type', attachment.mime_type);
    res.setHeader(
      'Content-Disposition',
      `attachment; filename="${attachment.original_name}"`
    );
    res.sendFile(filePath);
  } catch (err) {
    console.error('Download error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});
