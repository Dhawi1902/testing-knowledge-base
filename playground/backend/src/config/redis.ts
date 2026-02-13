import { createClient } from 'redis';
import { config } from './index';

export const redisClient = createClient({
  url: config.redis.url,
});

redisClient.on('error', (err) => {
  console.error('Redis error:', err);
});

export async function connectRedis(): Promise<void> {
  await redisClient.connect();
  console.log('Connected to Redis');
}
