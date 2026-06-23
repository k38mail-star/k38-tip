const { chromium } = require('playwright');

(async () => {
  const url = process.env.TEST_URL || 'https://boboji.beer/';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } }); // iPhone 14
  
  try {
    // 1. 加载页面
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    
    // 2. 等待比赛卡片渲染（最多10秒）
    await page.waitForSelector('.mc', { timeout: 10000 });
    
    // 3. 检查卡片数量
    const cardCount = await page.$$eval('.mc', els => els.length);
    if (cardCount === 0) {
      throw new Error(`❌ 比赛卡片数量为0`);
    }
    console.log(`✅ 比赛卡片: ${cardCount}张`);
    
    // 4. 检查预测标签
    const recCount = await page.$$eval('.mc-rec', els => els.length);
    console.log(`${recCount > 0 ? '✅' : '⚠️'} 预测标签: ${recCount}个`);
    
    // 5. 检查每个卡片的关键元素
    const cardChecks = await page.$$eval('.mc', cards => 
      cards.map(c => ({
         hasCk: !!c.querySelector('.ck'),
         hasTeams: !!c.querySelector('.mc-teams'),
         hasPct: !!c.querySelector('.mc-pct'),
         hasLightning: c.innerHTML.includes('⚡'),
      }))
    );
    const brokenCards = cardChecks.filter(c => !c.hasCk || !c.hasTeams);
    if (brokenCards.length > 0) {
      throw new Error(`❌ ${brokenCards.length}张卡片结构异常`);
    }
    console.log(`✅ 卡片结构: ${cardChecks.length}张全部正常`);
    
    // 6. 截图存档
    await page.screenshot({ path: 'screenshot.png', fullPage: true });
    console.log('✅ 截图已保存: screenshot.png');
    
    // 7. 检查控制台报错
    const errors = await page.evaluate(() => {
      const entries = performance.getEntriesByType('resource');
      const failed = entries.filter(e => e.responseStatus >= 400);
      return failed.map(e => `${e.name} → ${e.responseStatus}`);
    });
    if (errors.length > 0) {
      console.warn(`⚠️ 资源加载失败: ${errors.length}个`);
      errors.forEach(e => console.warn(`  ${e}`));
    }
    
    console.log('\n🎉 视觉测试全部通过');
    process.exit(0);
    
  } catch (e) {
    // 失败时也截图，方便排查
    await page.screenshot({ path: 'screenshot_failed.png', fullPage: true }).catch(() => {});
    console.error(`\n❌ 测试失败: ${e.message}`);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
