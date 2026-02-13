import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { redisClient } from '../config/redis';
import { config } from '../config';

const CSRF_PREFIX = 'csrf:';

export async function generateCsrfTokens(): Promise<{ _csrf: string; _formId: string }> {
  const _csrf = uuidv4();
  const _formId = uuidv4();

  // Store in Redis with TTL
  await redisClient.setEx(
    `${CSRF_PREFIX}${_formId}`,
    config.csrf.ttlSeconds,
    _csrf
  );

  return { _csrf, _formId };
}

export function validateCsrf(req: Request, res: Response, next: NextFunction): void {
  const _csrf = req.body._csrf || req.headers['x-csrf-token'];
  const _formId = req.body._formId || req.headers['x-form-id'];

  if (!_csrf || !_formId) {
    res.status(403).json({ error: 'CSRF tokens required' });
    return;
  }

  const key = `${CSRF_PREFIX}${_formId}`;

  redisClient.get(key).then(async (storedCsrf) => {
    if (!storedCsrf || storedCsrf !== _csrf) {
      res.status(403).json({ error: 'Invalid CSRF token' });
      return;
    }

    // Delete after use (one-time token)
    await redisClient.del(key);
    next();
  }).catch((err) => {
    console.error('CSRF validation error:', err);
    res.status(500).json({ error: 'Internal server error' });
  });
}
