// Playwright 配置文件
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',

  // 测试超时时间
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },

  // 失败时重试
  retries: process.env.CI ? 2 : 0,

  // 并行运行
  workers: process.env.CI ? 1 : 2,

  // 报告格式
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['list']
  ],

  use: {
    // 基础URL
    baseURL: 'https://boboji.beer',

    // 截图和视频
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',

    // 浏览器选项
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,

    // 用户代理
    userAgent: 'Playwright-K38-Test',
  },

  // 测试项目配置
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // Web服务器配置（如果需要本地测试）
  // webServer: {
  //   command: 'python app.py',
  //   port: 5000,
  //   timeout: 120 * 1000,
  //   reuseExistingServer: !process.env.CI,
  // },
});
