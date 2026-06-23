# K38-TIP 自动化测试文档

## 📋 测试体系概览

本项目包含完整的自动化测试和CI/CD流程，确保每次部署都经过严格验证。

## 🎭 Playwright 视觉测试

### 快速开始

```bash
# 1. 安装依赖
npm install

# 2. 安装浏览器
npm run install-browsers

# 3. 运行测试
npm test

# 4. 查看报告
npm run report
```

### 测试覆盖

✅ **10项完整测试**：
1. 页面加载和基础元素检查
2. 搜索框位置检查
3. 时间和时区选择器位置检查
4. 比赛卡片渲染和位置验证
5. 比赛卡片内容完整性
6. 智能组合按钮位置检查
7. API和前端数据一致性
8. 视觉回归截图对比
9. 响应式布局（移动端）
10. 性能检查 - 加载时间

### 测试命令

```bash
# 运行所有测试
npm test

# 带UI界面运行
npm run test:ui

# 只测试Chrome
npm run test:chrome

# 只测试移动端
npm run test:mobile

# 调试模式
npm run test:debug

# 显示浏览器窗口
npm run test:headed
```

## 🚀 部署后自动验证

每次部署后，自动执行完整的验证流程：

```bash
./post-deploy-check.sh
```

### 验证步骤

1. ⏳ 等待服务器重启
2. 📡 检查API健康状态
3. 🔍 验证部署版本
4. 🎭 运行Playwright视觉测试
5. 💨 执行快速烟雾测试
6. 📊 生成验证报告

## 🔄 CI/CD 流程

### GitHub Actions 自动化

**触发条件**：
- Push到main分支
- Pull Request到main分支

**流程**：
1. **视觉回归测试** (所有PR和Push)
   - 运行Playwright测试
   - 上传测试报告
   - 失败时上传截图
   - 在PR中评论结果

2. **部署后验证** (仅main分支)
   - 等待部署完成
   - 执行post-deploy-check.sh
   - 失败时发送通知
   - 创建部署记录

3. **性能测试** (仅main分支)
   - Lighthouse性能评分
   - 上传性能报告

## 🐛 问题排查

### 测试失败怎么办？

1. **查看报告**：
   ```bash
   npm run report
   ```

2. **查看失败截图**：
   - 位置: `test-results/`
   - 每个失败测试都有截图

3. **调试模式运行**：
   ```bash
   npm run test:debug
   ```

### 常见问题

**Q: 测试超时？**
A: 检查网络连接，或增加 `playwright.config.js` 中的 `timeout` 值

**Q: 视觉回归失败？**
A: 使用 `npx playwright test --update-snapshots` 更新基准截图

**Q: 元素未找到？**
A: 检查选择器是否正确，或增加 `waitForSelector` 超时时间

## 📁 目录结构

```
k38-tip/
├── tests/
│   └── visual-test.spec.js       # Playwright测试用例
├── .github/
│   └── workflows/
│       └── ci-cd.yml              # CI/CD配置
├── playwright.config.js           # Playwright配置
├── package.json                   # 依赖和脚本
├── post-deploy-check.sh           # 部署后验证脚本
├── playwright-report/             # 测试报告（自动生成）
└── test-results/                  # 测试结果（自动生成）
```

## 🎯 最佳实践

### 开发流程

1. **本地开发**：
   ```bash
   # 修改代码后运行测试
   npm test
   ```

2. **提交前检查**：
   ```bash
   # 确保所有测试通过
   npm test
   git add .
   git commit -m "fix: 修复XXX问题"
   ```

3. **PR审查**：
   - 等待CI测试通过
   - 查看测试报告
   - 合并到main

4. **部署后验证**：
   - CI自动执行验证
   - 查看验证报告
   - 确认线上功能正常

## 🔐 质量保证

### 防止问题重现

1. ✅ 每个bug修复都添加对应的测试用例
2. ✅ 部署前必须通过所有测试
3. ✅ 部署后自动验证关键功能
4. ✅ 视觉回归测试捕获UI变化
5. ✅ 多浏览器、多设备测试

### 测试金字塔

```
      /\
     /  \  E2E测试 (Playwright)
    /____\
   /      \
  / 集成测试 \
 /___________\
/             \
/   单元测试    \
/______________\
```

## 📞 支持

遇到问题？联系 K38 团队：
- Email: k38mail@gmail.com
- GitHub Issues: https://github.com/k38mail-star/k38-tip/issues

---

**版本**: v1.1.5  
**最后更新**: 2026-06-23  
**维护者**: Claude Code + K38 Team
