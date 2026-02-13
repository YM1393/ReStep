import { defineConfig } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const backendDir = path.resolve(__dirname, '..', 'backend');

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 2,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command: `"${path.join(backendDir, 'venv', 'Scripts', 'python.exe')}" -m uvicorn app.main:app --port 8000`,
      cwd: backendDir,
      port: 8000,
      timeout: 30000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev',
      port: 5173,
      timeout: 15000,
      reuseExistingServer: true,
    },
  ],
});
