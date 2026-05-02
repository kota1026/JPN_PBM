import { expect, test } from '@playwright/test';

/**
 * 江東区フラッグシップ通しシナリオ E2E。
 *
 * 1. tokyo.html: 監査・peg・加盟店 CP-6 承認 UI を確認
 * 2. citizen.html: 認証 → 災害用 QR を発行
 * 3. retailer.html: オフライン coupon キュー + flush の UI を確認
 *
 * Note: 実際の data flow (mint/issue/spend) は backend テストで網羅済。
 * E2E は「画面が崩れていない」「ボタンが押せて API 200 が返る」レベルの保証のみ。
 */

test.describe('フラッグシップ通しシナリオ', () => {
  test('① 都管理画面: 監査/Peg/加盟店/CP違反 セクションが見える', async ({ page }) => {
    await page.goto('/ui/tokyo.html');

    await expect(page.locator('h2', { hasText: 'トレジャリー' })).toBeVisible();
    await expect(page.locator('h2', { hasText: '準備金監査' })).toBeVisible();
    await expect(page.locator('h2', { hasText: '加盟店 (CP-6 オフライン承認)' })).toBeVisible();
    await expect(page.locator('h2', { hasText: 'CP-1〜CP-6 違反ダッシュボード' })).toBeVisible();
    await expect(page.locator('h2', { hasText: '助成金プログラム' })).toBeVisible();

    // 監査 KPI が "-" でないこと (= API が応答した)
    await page.waitForFunction(() => {
      const v = document.getElementById('auditHealth')?.textContent || '';
      return v && v.trim() !== '-';
    }, { timeout: 5000 });
  });

  test('② 住民マイページ: 認証 → CP-6 QR 発行', async ({ page }) => {
    await page.goto('/ui/citizen.html');
    await page.fill('input[name=maina_id]', 'MN-E2E-001');
    await page.fill('input[name=ward]', '江東区');
    await page.fill('input[name=address]', '東京都江東区豊洲1-1-1');
    await page.click('button[type=submit]');

    // QR が描画される (canvas/svg のいずれか)
    await expect(page.locator('#qrWrap canvas, #qrWrap svg')).toBeVisible({ timeout: 5000 });

    // CP-6 セクションが表示
    await expect(page.locator('h2', { hasText: '災害時オフライン QR を事前取得' })).toBeVisible();
  });

  test('③ 加盟店レジ: CP-6 オフラインモードのキュー UI', async ({ page }) => {
    await page.goto('/ui/retailer.html');
    await expect(page.locator('h2', { hasText: 'CP-6 ネット断モード' })).toBeVisible();
    // 初期キュー件数 = 0
    await expect(page.locator('#queueCount')).toHaveText('0');
    // ボタン群が存在
    await expect(page.locator('#scanCouponBtn')).toBeVisible();
    await expect(page.locator('#flushQueueBtn')).toBeVisible();
    await expect(page.locator('#clearQueueBtn')).toBeVisible();
  });

  test('④ EBPM: violations endpoint が 200 を返す', async ({ request }) => {
    const r = await request.get('/ebpm/violations');
    expect(r.ok()).toBeTruthy();
    const body = await r.json();
    expect(Array.isArray(body)).toBeTruthy();
  });

  // ----------------- 戦略会議 #6 採択 D: OAuth + 多年度ビュー追加 -----------------

  test('⑤ 住民マイページ: Phase 1/2 OAuth ラジオが切替可能', async ({ page }) => {
    await page.goto('/ui/citizen.html');
    const direct = page.locator('input[name=authMode][value=direct]');
    const oauth = page.locator('input[name=authMode][value=oauth]');
    await expect(direct).toBeChecked();
    await oauth.check();
    await expect(oauth).toBeChecked();
    await expect(direct).not.toBeChecked();
  });

  test('⑥ 都管理画面: 多年度予算ビューのセクションが存在', async ({ page }) => {
    await page.goto('/ui/tokyo.html');
    await expect(page.locator('h2', { hasText: '多年度予算ビュー' })).toBeVisible();
    await expect(page.locator('#fyProgramSel')).toBeVisible();
    await expect(page.locator('#fyRefreshBtn')).toBeVisible();
  });

  test('⑦ Treasury: keys/rotation + migrations/status が 200', async ({ request }) => {
    const r1 = await request.get('/treasury/keys/rotation');
    expect(r1.ok()).toBeTruthy();
    const body1 = await r1.json();
    expect(body1).toHaveProperty('configured_keys');

    const r2 = await request.get('/treasury/migrations/status');
    expect(r2.ok()).toBeTruthy();
    const body2 = await r2.json();
    expect(body2).toHaveProperty('dialect');
    expect(Array.isArray(body2.applied)).toBeTruthy();
  });
});
