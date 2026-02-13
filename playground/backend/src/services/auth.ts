import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { config } from '../config';
import { queryOne, queryDb } from '../config/database';

export interface UserPayload {
  userId: number;
  email: string;
  role: string;
}

export function generateAccessToken(payload: UserPayload): string {
  return jwt.sign(payload, config.jwt.secret, {
    expiresIn: config.jwt.expiresIn,
  });
}

export function generateRefreshToken(): string {
  return crypto.randomBytes(40).toString('hex');
}

export function verifyAccessToken(token: string): UserPayload {
  return jwt.verify(token, config.jwt.secret) as UserPayload;
}

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10);
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  // pgcrypto uses $2a$ prefix, bcryptjs supports it
  return bcrypt.compare(password, hash);
}

export async function storeRefreshToken(userId: number, token: string): Promise<void> {
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days
  await queryDb(
    'INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES ($1, $2, $3)',
    [userId, tokenHash, expiresAt]
  );
}

export async function validateRefreshToken(token: string): Promise<{ userId: number } | null> {
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
  const row = await queryOne<{ user_id: number }>(
    'SELECT user_id FROM refresh_tokens WHERE token_hash = $1 AND expires_at > NOW()',
    [tokenHash]
  );
  return row ? { userId: row.user_id } : null;
}

export async function revokeRefreshToken(token: string): Promise<void> {
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
  await queryDb('DELETE FROM refresh_tokens WHERE token_hash = $1', [tokenHash]);
}

export async function revokeAllUserRefreshTokens(userId: number): Promise<void> {
  await queryDb('DELETE FROM refresh_tokens WHERE user_id = $1', [userId]);
}
