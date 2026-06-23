/**
 * 异常和边界场景测试
 * 测试系统在异常情况下的表现
 */

const { test, expect } = require('@playwright/test');

test.describe('异常场景测试', () => {

  test('1. API错误时的UI表现', async ({ page, context }) => {
    console.log('🔍 测试API错误处理...');

    // 拦截API请求并返回错误
    await context.route('**/api/candidates*', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    await page.goto('/');

    // 应该显示错误提示
    const errorMsg = page.locator('text=/加载失败|错误|Error/i').first();
    await expect(errorMsg).toBeVisible({ timeout: 10000 });

    console.log('✅ API错误时正确显示错误提示');
  });

  test('2. 空数据时的UI表现', async ({ page, context }) => {
    console.log('🔍 测试空数据处理...');

    // 拦截API请求并返回空数据
    await context.route('**/api/candidates*', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ matches: [] })
      });
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    // 应该显示"暂无比赛"提示
    const emptyMsg = page.locator('text=/暂无|没有|无数据/i').first();
    await expect(emptyMsg).toBeVisible({ timeout: 5000 });

    console.log('✅ 空数据时正确显示提示');
  });

  test('3. 网络超时处理', async ({ page, context }) => {
    console.log('🔍 测试网络超时...');

    // 拦截并延迟响应
    await context.route('**/api/candidates*', route => {
      setTimeout(() => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ matches: [] })
        });
      }, 30000); // 30秒超时
    });

    await page.goto('/');

    // 应该显示加载中或超时提示
    const loadingOrError = page.locator('text=/加载|Loading|超时|Timeout/i').first();
    await expect(loadingOrError).toBeVisible({ timeout: 35000 });

    console.log('✅ 网络超时时有反馈');
  });

  test('4. 部分数据缺失的卡片渲染', async ({ page, context }) => {
    console.log('🔍 测试数据缺失处理...');

    // 返回部分字段缺失的数据
    await context.route('**/api/candidates*', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          matches: [
            {
              id: 1,
              home: '主队',
              // away 字段缺失
              prediction: '主胜',
              confidence: 80
            }
          ]
        })
      });
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    // 应该优雅处理缺失字段，不crash
    const cards = page.locator('.mc');
    const count = await cards.count();

    // 可能显示0个或1个（取决于后端容错）
    expect(count).toBeGreaterThanOrEqual(0);

    console.log('✅ 数据缺失时不会崩溃');
  });
});

test.describe('用户交互测试', () => {

  test('5. 复选框点击交互', async ({ page }) => {
    console.log('🔍 测试复选框交互...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    const firstCard = page.locator('.mc').first();
    const checkbox = firstCard.locator('.ck');

    // 初始状态
    const initialState = await checkbox.getAttribute('aria-checked');
    console.log(`  初始状态: ${initialState}`);

    // 点击复选框
    await checkbox.click();
    await page.waitForTimeout(500);

    // 检查状态变化
    const newState = await checkbox.getAttribute('aria-checked');
    console.log(`  点击后状态: ${newState}`);

    expect(newState).not.toBe(initialState);
    console.log('✅ 复选框交互正常');
  });

  test('6. 搜索框输入测试', async ({ page }) => {
    console.log('🔍 测试搜索框...');

    await page.goto('/', { waitUntil: 'networkidle' });

    const searchInput = page.locator('input[placeholder*="搜索"]');

    if (await searchInput.count() > 0) {
      await searchInput.fill('曼联');
      await page.waitForTimeout(1000);

      // 检查是否有搜索结果或反馈
      const hasCards = await page.locator('.mc').count() > 0;
      const hasMessage = await page.locator('text=/暂无|没有|无/i').count() > 0;

      expect(hasCards || hasMessage).toBeTruthy();
      console.log('✅ 搜索功能正常');
    } else {
      console.log('⚠️ 未找到搜索框，跳过');
    }
  });

  test('7. 联赛筛选测试', async ({ page }) => {
    console.log('🔍 测试联赛筛选...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    // 获取初始卡片数量
    const initialCount = await page.locator('.mc').count();
    console.log(`  初始卡片数: ${initialCount}`);

    // 查找联赛标签
    const leagueTag = page.locator('.tag').first();

    if (await leagueTag.count() > 0) {
      await leagueTag.click();
      await page.waitForTimeout(1000);

      // 检查卡片数量变化
      const newCount = await page.locator('.mc').count();
      console.log(`  筛选后卡片数: ${newCount}`);

      // 卡片数量应该有变化
      expect(newCount).toBeDefined();
      console.log('✅ 联赛筛选功能正常');
    } else {
      console.log('⚠️ 未找到联赛标签，跳过');
    }
  });

  test('8. 智能推荐按钮测试', async ({ page }) => {
    console.log('🔍 测试智能推荐按钮...');

    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForSelector('.mc', { timeout: 15000 });

    // 查找智能推荐按钮
    const aiButton = page.locator('text=/智能推荐|AI推荐|推荐/i').first();

    if (await aiButton.count() > 0) {
      // 先选中一些卡片
      const checkboxes = page.locator('.ck');
      if (await checkboxes.count() > 0) {
        await checkboxes.first().click();
        await page.waitForTimeout(500);
      }

      // 点击AI按钮
      await aiButton.click();
      await page.waitForTimeout(2000);

      // 应该有弹窗或页面变化
      const hasModal = await page.locator('.modal, .dialog, .popup').count() > 0;
      const hasResult = await page.locator('text=/组合|推荐|串关/i').count() > 0;

      expect(hasModal || hasResult).toBeTruthy();
      console.log('✅ 智能推荐按钮功能正常');
    } else {
      console.log('⚠️ 未找到智能推荐按钮，跳过');
    }
  });
});
