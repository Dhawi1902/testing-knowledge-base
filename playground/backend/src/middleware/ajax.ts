import { Request, Response, NextFunction } from 'express';

/**
 * Enforces AJAX headers on API routes.
 * Backend requires Accept: application/json and X-Requested-With: XMLHttpRequest
 * for AJAX API calls. This forces JMeter to include these headers.
 *
 * Exempt routes (curl-friendly): /api/admin/health, /api/admin/seed
 */
export function requireAjaxHeaders(req: Request, res: Response, next: NextFunction): void {
  // Skip enforcement for admin utility endpoints
  if (req.path === '/health' || req.path === '/seed') {
    next();
    return;
  }

  const accept = req.headers.accept || '';
  const xRequestedWith = req.headers['x-requested-with'] || '';

  if (!accept.includes('application/json')) {
    res.status(406).json({
      error: 'Not Acceptable',
      message: 'Accept: application/json header required',
    });
    return;
  }

  if (xRequestedWith !== 'XMLHttpRequest') {
    res.status(406).json({
      error: 'Not Acceptable',
      message: 'X-Requested-With: XMLHttpRequest header required',
    });
    return;
  }

  next();
}
