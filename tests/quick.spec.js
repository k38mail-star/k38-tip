/**
 * Layer 1: 部署时快速检查
 * 目标：2-3分钟内验证核心功能
 * 失败策略：阻断部署
 *
 * 基于小五方案，增强关键检查
 */

const { test, expect } = require('@playwright/test');

// P0-2: 限制只在Chrome上运行，避免15分钟等待
test.use({ browserName: 'chromium' });

test.describe('Layer 1: 部署快速验证', () => {

  test('1. API健康检查', async ({ request }) => {
    console.log('🔍 检查API可用性...');

    const resp = await request.get('/api/version');
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    console.log(`✅ API版本: ${data.version} (${data.commit.slice(0,7)})`);
  });

  test('2. API返回数据', async ({ request }) => {
    console.log('🔍 检查API数据...');

    const resp = await request.get('/api/candidates?limit=10');
    expect(resp.ok()).toBeTruthy();

    const data = await resp.json();
    expect(data.matches).toBeDefined();
    expect(data.matches.length).toBeGreaterThan(0);

    console.log(`✅ API返回 ${data.matches.length} 场比赛`);
  });

  test('3. 页面可访问', async ({ page }) => {
    console.log('🔍 检查页面加载...');

    await page.goto('/', { timeout: 10000 });
    await expect(page).toHaveTitle(/波波鸡/);

    console.log('✅ 页面加载成功');
  });

  test('4. 比赛卡片数量>0 (小五检查项)', async ({ page }) => {
    console.log('🔍 检查比赛卡片...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    const cardCount = await page.locator('.mc').count();
    expect(cardCount).toBeGreaterThan(0);

    console.log(`✅ 发现 ${cardCount} 个比赛卡片`);
  });

  test('5. 卡片结构完整 (小五检查项)', async ({ page }) => {
    console.log('🔍 检查卡片结构...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    const firstCard = page.locator('.mc').first();

    // 复选框
    await expect(firstCard.locator('.ck')).toBeVisible();
    console.log('  ✓ 复选框存在');

    // 球队名
    const teamNames = firstCard.locator('.mc-t-name');
    expect(await teamNames.count()).toBeGreaterThanOrEqual(2);
    console.log('  ✓ 球队名称存在');

    // 胜率
    await expect(firstCard.locator('.mc-pct')).toBeVisible();
    console.log('  ✓ 胜率显示存在');

    console.log('✅ 卡片结构完整');
  });

  test('6. 预测标签存在 (小五检查项)', async ({ page }) => {
    console.log('🔍 检查预测标签...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    const firstCard = page.locator('.mc').first();
    const predTag = firstCard.locator('.mc-rec');

    await expect(predTag).toBeVisible();
    console.log('✅ 预测标签存在');
  });

  test('7. 控制台无严重错误 (小五检查项)', async ({ page }) => {
    console.log('🔍 监控控制台错误...');

    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    page.on('pageerror', err => {
      errors.push(err.message);
    });

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    // 过滤掉无关紧要的错误
    const criticalErrors = errors.filter(e =>
      e.includes('404') ||
      e.includes('500') ||
      e.includes('Failed to fetch') ||
      e.includes('Network error')
    );

    if (criticalErrors.length > 0) {
      console.log('⚠️ 发现控制台错误:', criticalErrors);
      // 记录但不阻断
    } else {
      console.log('✅ 控制台无严重错误');
    }

    // 严重错误才阻断
    const blockingErrors = criticalErrors.filter(e => e.includes('500'));
    expect(blockingErrors.length).toBe(0);
  });

  test('8. 截图存档', async ({ page }) => {
    console.log('📸 生成部署截图...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    // 桌面截图
    await page.screenshot({
      path: 'test-results/deploy-success-desktop.png',
      fullPage: true
    });
    console.log('✅ 桌面版截图已保存');

    // 移动端截图
    await page.setViewportSize({ width: 375, height: 667 });
    await page.screenshot({
      path: 'test-results/deploy-success-mobile.png',
      fullPage: true
    });
    console.log('✅ 移动版截图已保存');
  });
});
