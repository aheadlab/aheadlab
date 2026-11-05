import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests', timeout: 60000, workers: 1, fullyParallel: false,
  use: { baseURL: process.env.BASE_URL || 'http://127.0.0.1:8501', viewport: { width: 1440, height: 1000 }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  reporter: [['list'], ['html', { open: 'never' }]],
  webServer: process.env.START_API === '1' ? {
    command: 'python -m uvicorn solarcast.api:app --host 127.0.0.1 --port 8501',
    url: 'http://127.0.0.1:8501/api/health', timeout: 60000,
  } : undefined,
});
