/**
 * Playwright 完整视觉测试
 * 安装: npm install -D @playwright/test
 * 运行: npx playwright test
 */

const { test, expect } = require('@playwright/test');

test.describe('K38-TIP 完整视觉测试', () => {

  test('1. 页面加载和基础元素检查', async ({ page }) => {
    console.log('🔍 访问页面...');
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });

    // 检查标题
    await expect(page).toHaveTitle(/波波鸡/);
    console.log('✅ 页面标题正确');

    // 检查关键容器存在
    await expect(page.locator('body')).toBeVisible();
    console.log('✅ 页面body加载完成');
  });

  test('2. 搜索框位置检查', async ({ page }) => {
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // 检查搜索框
    const searchInput = page.locator('input[placeholder*="搜索"]');
    await expect(searchInput).toBeVisible();

    // 检查搜索框位置（应该在页面上部）
    const searchBox = await searchInput.boundingBox();
    expect(searchBox.y).toBeLessThan(300); // 搜索框应该在页面上半部分
    console.log(`✅ 搜索框位置正确: Y=${searchBox.y}px`);
  });

  test('3. 时间和时区选择器位置检查', async ({ page }) => {
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // 查找时间选择器（根据实际DOM结构调整）
    const dateSelector = page.locator('.date-selector, [class*="date"], [class*="time"]').first();
    if (await dateSelector.count() > 0) {
      await expect(dateSelector).toBeVisible();
      const dateBox = await dateSelector.boundingBox();
      console.log(`✅ 时间选择器位置: Y=${dateBox.y}px`);
    }
  });

  test('4. 比赛卡片必须渲染且位置正确', async ({ page }) => {
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    console.log('⏳ 等待比赛数据加载...');

    // 等待比赛卡片出现（最多10秒）
    await page.waitForSelector('.mc', { timeout: 10000 });

    // 检查比赛卡片数量
    const matchCards = await page.locator('.mc').count();
    expect(matchCards).toBeGreaterThan(0);
    console.log(`✅ 发现 ${matchCards} 个比赛卡片`);

    // 检查第一个卡片的位置
    const firstCard = page.locator('.mc').first();
    await expect(firstCard).toBeVisible();

    const cardBox = await firstCard.boundingBox();
    expect(cardBox.y).toBeGreaterThan(100); // 卡片应该在搜索框下方
    expect(cardBox.y).toBeLessThan(800); // 第一个卡片不应该太靠下
    console.log(`✅ 第一个卡片位置正确: Y=${cardBox.y}px`);
  });

  test('5. 比赛卡片内容完整性检查', async ({ page }) => {
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 10000 });

    const firstCard = page.locator('.mc').first();

    // 检查队伍名称
    const teams = firstCard.locator('.mc-t-name');
    expect(await teams.count()).toBeGreaterThanOrEqual(2);
    console.log('✅ 队伍名称存在');

    // 检查胜率
    const confidence = firstCard.locator('.mc-pct .vl');
    await expect(confidence).toBeVisible();
    const confText = await confidence.textContent();
    expect(confText).toMatch(/\d+%/);
    console.log(`✅ 胜率显示正常: ${confText}`);

    // 检查VS标识
    const vs = firstCard.locator('.mc-vs');
    await expect(vs).toBeVisible();
    console.log('✅ VS标识存在');
  });

  test('6. 智能组合按钮位置检查', async ({ page }) => {
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // 检查底部按钮
    const smartBtn = page.locator('text=/智能组合|智能推荐/').first();
    if (await smartBtn.count() > 0) {
      await expect(smartBtn).toBeVisible();
      const btnBox = await smartBtn.boundingBox();

      // 按钮应该在页面下方
      const pageHeight = await page.evaluate(() => window.innerHeight);
      expect(btnBox.y).toBeGreaterThan(pageHeight * 0.5);
      console.log(`✅ 智能按钮位置正确: Y=${btnBox.y}px (页面高度: ${pageHeight}px)`);
    }
  });

  test('7. API和前端数据一致性', async ({ page, request }) => {
    // 调用API
    const apiResp = await request.get('https://boboji.beer/api/candidates?limit=10');
    const apiData = await apiResp.json();
    const apiCount = apiData.matches.length;
    console.log(`📊 API返回 ${apiCount} 场比赛`);

    // 检查前端渲染
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 10000 });
    const domCount = await page.locator('.mc').count();
    console.log(`📊 前端渲染 ${domCount} 个卡片`);

    // 断言：前端至少要渲染部分数据
    expect(domCount).toBeGreaterThan(0);
    expect(domCount).toBeLessThanOrEqual(apiCount);
    console.log('✅ 数据一致性检查通过');
  });

  test('8. 视觉回归 - 截图对比', async ({ page }) => {
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 10000 });

    // 等待所有图片加载
    await page.waitForTimeout(2000);

    // 全页截图
    await expect(page).toHaveScreenshot('homepage-full.png', {
      fullPage: true,
      maxDiffPixels: 500 // 允许500像素差异
    });
    console.log('✅ 视觉回归截图完成');
  });

  test('9. 响应式布局检查（移动端）', async ({ page }) => {
    // 设置移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 10000 });

    const matchCards = await page.locator('.mc').count();
    expect(matchCards).toBeGreaterThan(0);
    console.log(`✅ 移动端渲染正常: ${matchCards} 个卡片`);

    // 移动端截图
    await expect(page).toHaveScreenshot('homepage-mobile.png', {
      fullPage: true,
      maxDiffPixels: 300
    });
  });

  test('10. 性能检查 - 加载时间', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('https://boboji.beer', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 10000 });
    const loadTime = Date.now() - startTime;

    // 页面应该在5秒内加载完成
    expect(loadTime).toBeLessThan(5000);
    console.log(`✅ 页面加载时间: ${loadTime}ms`);
  });
});
