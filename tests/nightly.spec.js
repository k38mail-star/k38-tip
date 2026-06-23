/**
 * Layer 3: 夜间全面测试
 * 目标：10-15分钟完整验证
 * 执行时机：每晚2点
 * 失败策略：创建Issue，次日修复
 */

const { test, expect } = require('@playwright/test');

test.describe('Layer 3: 夜间全面测试', () => {

  test('1. 多浏览器兼容性测试', async ({ page, browserName }) => {
    console.log(`🌐 测试浏览器: ${browserName}`);

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    const cardCount = await page.locator('.mc').count();
    expect(cardCount).toBeGreaterThan(0);

    console.log(`✅ ${browserName}: ${cardCount} 个卡片渲染正常`);
  });

  test('2. 多设备响应式测试', async ({ page }) => {
    const devices = [
      { name: 'Desktop', width: 1920, height: 1080 },
      { name: 'Laptop', width: 1366, height: 768 },
      { name: 'Tablet', width: 768, height: 1024 },
      { name: 'Mobile', width: 375, height: 667 },
    ];

    for (const device of devices) {
      console.log(`📱 测试设备: ${device.name} (${device.width}x${device.height})`);

      await page.setViewportSize({ width: device.width, height: device.height });
      await page.goto('/', { waitUntil: 'networkidle' });
      await page.waitForSelector('.mc', { timeout: 15000 });

      const cardCount = await page.locator('.mc').count();
      expect(cardCount).toBeGreaterThan(0);

      // 截图存档
      await page.screenshot({
        path: `test-results/nightly-${device.name.toLowerCase()}.png`,
        fullPage: true
      });

      console.log(`✅ ${device.name}: 渲染正常`);
    }
  });

  test('3. 性能压力测试', async ({ page }) => {
    console.log('⚡ 执行性能测试...');

    const iterations = 5;
    const loadTimes = [];

    for (let i = 0; i < iterations; i++) {
      const startTime = Date.now();
      await page.goto('/', { waitUntil: 'networkidle' });
      await page.waitForSelector('.mc', { timeout: 15000 });
      const loadTime = Date.now() - startTime;
      loadTimes.push(loadTime);

      console.log(`  第${i + 1}次加载: ${loadTime}ms`);
    }

    const avgLoadTime = loadTimes.reduce((a, b) => a + b, 0) / iterations;
    const maxLoadTime = Math.max(...loadTimes);

    console.log(`📊 平均加载时间: ${avgLoadTime.toFixed(0)}ms`);
    console.log(`📊 最大加载时间: ${maxLoadTime}ms`);

    // 平均加载时间应该<5秒
    expect(avgLoadTime).toBeLessThan(5000);
    // 最大加载时间应该<8秒
    expect(maxLoadTime).toBeLessThan(8000);

    console.log('✅ 性能测试通过');
  });

  test('4. API稳定性测试', async ({ request }) => {
    console.log('🔄 测试API稳定性...');

    const endpoints = [
      '/api/version',
      '/api/candidates?limit=10',
      '/api/candidates?limit=50',
    ];

    for (const endpoint of endpoints) {
      let successCount = 0;
      const iterations = 10;

      for (let i = 0; i < iterations; i++) {
        const resp = await request.get(endpoint);
        if (resp.ok()) successCount++;
      }

      const successRate = (successCount / iterations) * 100;
      console.log(`  ${endpoint}: ${successRate}% 成功率`);

      // 成功率应该>95%
      expect(successRate).toBeGreaterThanOrEqual(95);
    }

    console.log('✅ API稳定性测试通过');
  });

  test('5. 数据一致性测试', async ({ page, request }) => {
    console.log('🔍 测试数据一致性...');

    // 获取API数据
    const apiResp = await request.get('/api/candidates?limit=100');
    const apiData = await apiResp.json();
    const apiMatches = apiData.matches;

    console.log(`  API返回: ${apiMatches.length} 场比赛`);

    // 检查前端渲染
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    // 获取所有卡片
    const cards = page.locator('.mc');
    const cardCount = await cards.count();

    console.log(`  前端渲染: ${cardCount} 个卡片`);

    // 验证数据一致性
    expect(cardCount).toBeGreaterThan(0);
    expect(cardCount).toBeLessThanOrEqual(apiMatches.length);

    // 抽样检查前3个卡片的内容
    for (let i = 0; i < Math.min(3, cardCount); i++) {
      const card = cards.nth(i);
      const teamNames = card.locator('.mc-t-name');
      const nameCount = await teamNames.count();

      expect(nameCount).toBeGreaterThanOrEqual(2);
    }

    console.log('✅ 数据一致性测试通过');
  });

  test('6. 长时间运行稳定性', async ({ page }) => {
    console.log('⏱️ 测试长时间运行...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    // 模拟用户浏览30秒
    for (let i = 0; i < 6; i++) {
      await page.waitForTimeout(5000);

      // 检查卡片仍然存在
      const cardCount = await page.locator('.mc').count();
      expect(cardCount).toBeGreaterThan(0);

      console.log(`  ${(i + 1) * 5}秒后: ${cardCount} 个卡片`);
    }

    console.log('✅ 长时间运行稳定');
  });

  test('7. 资源加载完整性', async ({ page }) => {
    console.log('📦 检查资源加载...');

    const failedResources = [];

    page.on('requestfailed', request => {
      failedResources.push({
        url: request.url(),
        failure: request.failure().errorText
      });
    });

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });
    await page.waitForTimeout(3000);

    if (failedResources.length > 0) {
      console.log('⚠️ 发现加载失败的资源:');
      failedResources.forEach(r => {
        console.log(`  - ${r.url}: ${r.failure}`);
      });
    }

    // 关键资源不应该加载失败
    const criticalFailed = failedResources.filter(r =>
      r.url.includes('/api/') ||
      r.url.includes('.js') ||
      r.url.includes('.css')
    );

    expect(criticalFailed.length).toBe(0);
    console.log('✅ 所有关键资源加载成功');
  });

  test('8. 内存泄漏检测', async ({ page }) => {
    console.log('💾 检测内存使用...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    // 初始内存快照
    const metrics1 = await page.evaluate(() => {
      if (performance.memory) {
        return {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize
        };
      }
      return null;
    });

    if (metrics1) {
      console.log(`  初始JS堆: ${(metrics1.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`);

      // 模拟用户操作10秒
      await page.waitForTimeout(10000);

      // 再次测量
      const metrics2 = await page.evaluate(() => {
        return {
          usedJSHeapSize: performance.memory.usedJSHeapSize,
          totalJSHeapSize: performance.memory.totalJSHeapSize
        };
      });

      console.log(`  10秒后JS堆: ${(metrics2.usedJSHeapSize / 1024 / 1024).toFixed(2)} MB`);

      const increase = metrics2.usedJSHeapSize - metrics1.usedJSHeapSize;
      const increasePercent = (increase / metrics1.usedJSHeapSize) * 100;

      console.log(`  增长: ${increasePercent.toFixed(1)}%`);

      // 内存增长不应该超过50%
      expect(increasePercent).toBeLessThan(50);
    }

    console.log('✅ 内存使用正常');
  });
});
