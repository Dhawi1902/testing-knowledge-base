import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import { queryDb, queryOne } from '../config/database';
import { authenticate } from '../middleware/auth';
import { validateCsrf } from '../middleware/csrf';
import { requireAjaxHeaders } from '../middleware/ajax';

const UPLOAD_DIR = process.env.UPLOAD_DIR || '/app/uploads';
const AVATAR_DIR = path.join(UPLOAD_DIR, 'avatars');

// Ensure avatar directory exists
if (!fs.existsSync(AVATAR_DIR)) {
  fs.mkdirSync(AVATAR_DIR, { recursive: true });
}

const avatarStorage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, AVATAR_DIR),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${uuidv4()}${ext}`);
  },
});

const avatarUpload = multer({
  storage: avatarStorage,
  limits: { fileSize: 2 * 1024 * 1024 }, // 2 MB
  fileFilter: (_req, file, cb) => {
    const allowed = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (allowed.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error('Only image files (JPEG, PNG, GIF, WebP) are allowed'));
    }
  },
});

export const usersRouter = Router();

usersRouter.use(requireAjaxHeaders);
usersRouter.use(authenticate);

// GET /api/users - List users (for dropdowns)
usersRouter.get('/', async (_req: Request, res: Response) => {
  try {
    const users = await queryDb(
      `SELECT id, email, display_name, role FROM users WHERE role != 'admin' ORDER BY display_name`
    );
    res.json({ users });
  } catch (err) {
    console.error('List users error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/users/me - Current user profile
usersRouter.get('/me', async (req: Request, res: Response) => {
  try {
    const user = await queryOne(
      'SELECT id, email, display_name, role, is_verified, created_at FROM users WHERE id = $1',
      [req.user!.userId]
    );

    if (!user) {
      res.status(404).json({ error: 'User not found' });
      return;
    }

    res.json(user);
  } catch (err) {
    console.error('Get profile error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /api/users/me - Update profile
usersRouter.put('/me', async (req: Request, res: Response) => {
  try {
    const { displayName } = req.body;

    if (!displayName) {
      res.status(400).json({ error: 'Display name is required' });
      return;
    }

    const user = await queryOne(
      'UPDATE users SET display_name = $1, updated_at = NOW() WHERE id = $2 RETURNING id, email, display_name, role',
      [displayName, req.user!.userId]
    );

    res.json(user);
  } catch (err) {
    console.error('Update profile error:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /api/users/me/avatar - Upload avatar
// multer parses multipart before CSRF validation
usersRouter.post(
  '/me/avatar',
  avatarUpload.single('avatar'),
  validateCsrf,
  async (req: Request, res: Response) => {
    try {
      if (!req.file) {
        res.status(400).json({ error: 'No avatar file uploaded. Send as multipart field named "avatar"' });
        return;
      }

      const avatarUrl = `/api/users/avatars/${req.file.filename}`;

      res.json({
        message: 'Avatar uploaded',
        avatarUrl,
        fileName: req.file.originalname,
        size: req.file.size,
      });
    } catch (err) {
      console.error('Avatar upload error:', err);
      res.status(500).json({ error: 'Internal server error' });
    }
  }
);

// GET /api/users/avatars/:filename - Serve avatar image
usersRouter.get('/avatars/:filename', (req: Request, res: Response) => {
  const filePath = path.join(AVATAR_DIR, req.params.filename);

  if (!fs.existsSync(filePath)) {
    res.status(404).json({ error: 'Avatar not found' });
    return;
  }

  res.sendFile(filePath);
});
