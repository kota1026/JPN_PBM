import { defineConfig, devices } from '@playwright/test';

/**
 * 通しシナリオ E2E (戦略会議 #3 採択 #2)。
 * tokyo → citizen → retailer の 3 画面を 1 ブラウザ走査で検証する。
 *
 * 起動方法:
 *   # 1) backend をローカルで起動
 *   cd backend && uvicorn app.main:app --port 8000
 *   # 2) (別ターミナル) e2e を実行
 *   cd e2e && npx playwright test
 */
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL: process.env.PBM_BASE_URL || 'http://localhost:8000',
    headless: true,
    viewport: { width: 1280, height: 800 },
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
