import { defineConfig } from '@playwright/test';

const PORT = process.env.WEBAPP_PORT || '9090';
const BASE_URL = `http://127.0.0.1:${PORT}/perftest/`;

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 1,
  use: {
    baseURL: BASE_URL,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  outputDir: './test-results/artifacts',
  reporter: [
    ['html', { outputFolder: './test-results/html', open: 'never' }],
    ['list'],
  ],
  webServer: {
    command: `python -m uvicorn main:app --host 127.0.0.1 --port ${PORT}`,
    cwd: '../../',
    port: Number(PORT),
    timeout: 15_000,
    reuseExistingServer: true,
  },
});
