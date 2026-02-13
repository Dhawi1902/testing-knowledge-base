import { Request, Response, NextFunction } from 'express';

// Simple in-memory rate limiter
const requests: Map<string, { count: number; resetAt: number }> = new Map();

// Clean up stale entries every 5 minutes
setInterval(() => {
  const now = Date.now();
  for (const [key, value] of requests.entries()) {
    if (value.resetAt < now) {
      requests.delete(key);
    }
  }
}, 5 * 60 * 1000);

export function rateLimit(maxRequests: number, windowMs: number) {
  return (req: Request, res: Response, next: NextFunction): void => {
    const key = req.ip || req.socket.remoteAddress || 'unknown';
    const now = Date.now();
    const entry = requests.get(key);

    if (!entry || entry.resetAt < now) {
      requests.set(key, { count: 1, resetAt: now + windowMs });
      res.setHeader('X-RateLimit-Limit', maxRequests);
      res.setHeader('X-RateLimit-Remaining', maxRequests - 1);
      next();
      return;
    }

    entry.count++;

    if (entry.count > maxRequests) {
      const retryAfter = Math.ceil((entry.resetAt - now) / 1000);
      res.setHeader('Retry-After', retryAfter);
      res.setHeader('X-RateLimit-Limit', maxRequests);
      res.setHeader('X-RateLimit-Remaining', 0);
      res.status(429).json({
        error: 'Too many requests. Please try again later.',
        retryAfter,
      });
      return;
    }

    res.setHeader('X-RateLimit-Limit', maxRequests);
    res.setHeader('X-RateLimit-Remaining', maxRequests - entry.count);
    next();
  };
}
