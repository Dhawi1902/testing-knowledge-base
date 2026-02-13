import { pool } from '../config/database';
import fs from 'fs';
import path from 'path';

/**
 * Re-seeds the database to a known state.
 * Reads and executes the init.sql file (same one used on first boot).
 */
export async function reseedDatabase(): Promise<void> {
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    // Drop all data (order matters due to foreign keys)
    await client.query('DELETE FROM admin_sessions');
    await client.query('DELETE FROM export_jobs');
    await client.query('DELETE FROM verification_tokens');
    await client.query('DELETE FROM schedules');
    await client.query('DELETE FROM attachments');
    await client.query('DELETE FROM comments');
    await client.query('DELETE FROM refresh_tokens');
    await client.query('DELETE FROM tasks');
    await client.query('DELETE FROM users');

    // Reset sequences
    await client.query('ALTER SEQUENCE users_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE tasks_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE comments_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE refresh_tokens_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE attachments_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE schedules_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE verification_tokens_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE export_jobs_id_seq RESTART WITH 1');
    await client.query('ALTER SEQUENCE admin_sessions_id_seq RESTART WITH 1');

    // Re-run the seed portion of init.sql
    // In Docker, db/ is mounted at /db. Locally, it's relative to project root.
    const initSqlPath = fs.existsSync('/db/init.sql')
      ? '/db/init.sql'
      : path.resolve(__dirname, '../../../db/init.sql');
    const fullSql = fs.readFileSync(initSqlPath, 'utf-8');

    // Extract everything after "-- SEED DATA"
    const seedMarker = '-- SEED DATA';
    const seedIndex = fullSql.indexOf(seedMarker);
    if (seedIndex === -1) {
      throw new Error('Seed data marker not found in init.sql');
    }
    const seedSql = fullSql.substring(seedIndex);

    await client.query(seedSql);
    await client.query('COMMIT');

    console.log('Database re-seeded successfully');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
}
