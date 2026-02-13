import express from 'express';
import cors from 'cors';
import cookieParser from 'cookie-parser';
import { config } from './config';
import { connectRedis } from './config/redis';
import { pool } from './config/database';
import { authRouter } from './routes/auth';
import { tasksRouter } from './routes/tasks';
import { usersRouter } from './routes/users';
import { dashboardRouter } from './routes/dashboard';
import { adminRouter } from './routes/admin';
import { filesRouter } from './routes/files';
import { schedulesRouter } from './routes/schedules';
import { scheduleConfirmRouter } from './routes/scheduleConfirm';
import { reportsRouter } from './routes/reports';
import { exportsRouter } from './routes/exports';

const app = express();

// Middleware
app.use(cors({
  origin: config.cors.origin,
  credentials: true,
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// Routes
app.use('/api/auth', authRouter);
app.use('/api/tasks', tasksRouter);
app.use('/api/users', usersRouter);
app.use('/api/dashboard', dashboardRouter);
app.use('/api/admin', adminRouter);
app.use('/api/files', filesRouter);
app.use('/api/tasks', schedulesRouter);       // /api/tasks/:id/schedule(s)
app.use('/api/schedules', scheduleConfirmRouter); // /api/schedules/:confirmationId/...
app.use('/api/reports', reportsRouter);
app.use('/api/exports', exportsRouter);
app.use('/admin', adminRouter);               // /admin/login (cookie-based admin page)

// 404 handler
app.use((_req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
async function start() {
  try {
    // Test database connection
    await pool.query('SELECT 1');
    console.log('Connected to PostgreSQL');

    // Connect to Redis
    await connectRedis();

    app.listen(config.port, () => {
      console.log(`TaskFlow backend running on port ${config.port}`);
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
}

start();
