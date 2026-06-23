# 波波鸡配啤酒 🐔⚽🍺 — Phase 1 优化任务

> 给 CC（Claude Code）执行的 task 清单
> 优先级已排序，按顺序做

---

## 🔴 P0 — 必须先修（现有bug）

### 1. 重复match_id去重
- **文件**: app.py (api_generate_combos)
- **问题**: 前端可能发 `ids=1&ids=2&ids=1`，后端没去重，同一场比赛算两次
- **修复**: `match_ids = list(dict.fromkeys(match_ids))` 或 `set()`

### 2. 赔率缓存无限增长
- **文件**: app.py
- **问题**: `_odds_cache` 字典只增不减，没有大小限制
- **修复**: 跟 `_pred_cache` 一样加 `_MAX_ODDS_CACHE=200` + LRU淘汰

### 3. 底部栏与免责声明重叠
- **文件**: templates/v84-kimi-a.html
- **问题**: 底部 `bb` 固定栏和 `disclaimer` 都是 `position:fixed; bottom:0`，同时显示时重叠
- **修复**: disclaimer 放在 bb 下面，或者 bb 上移 disclaimer 的高度

### 4. 串关失败提示优化
- **文件**: templates/v84-kimi-a.html (showResult function)
- **问题**: 串关失败只显示"加载失败"，用户不知道原因
- **修复**: 区分"网络错误"、"组合太多"、"无有效组合"三种情况，分别给提示

### 5. calculate_ev 无用参数清理
- **文件**: odds_service.py
- **问题**: `pred_lose_prob` 和 `lose_odds` 两个参数接收了但函数体内从未使用
- **修复**: 删掉参数或加 `# noqa` 标记

---

## 🟠 P1 — 快速见效（半天能搞定的体验提升）

### 6. 前端请求缓存
- **实现**: 在 `load()` 函数里加 `st._cache = {}` Map
- **key**: `${date_from}_${date_to}_${lids.join(',')}`
- **value**: API 返回的数据
- **TTL**: 5分钟，过期删掉
- **效果**: 切"今天"→"3天"→切回"今天"秒开，不用重新请求

### 7. 足球按钮脉冲引导
- **实现**: 当 `st.picks.size >= 2` 时，给 `#gb` 加呼吸动画 `@keyframes pulse`
- **CSS**:
  ```css
  @keyframes pulse {
    0%, 100% { box-shadow: 0 4px 20px rgba(124,92,191,.4); }
    50% { box-shadow: 0 4px 30px rgba(124,92,191,.7); }
  }
  .fb.ready { animation: pulse 1.5s ease-in-out infinite; }
  ```
- **时机**: `up()` 函数里 `n>=2` 时加 `.ready` 类

### 8. 虚拟列表（比赛分页）
- **实现**: 已有 `_pageSize=15` 和 "显示更多"按钮，但滚动到顶部时联赛标签不固定
- **补充**: 把 `ml` 区域加 `max-height` 和 `overflow-y: auto`，让列表可滚动但不影响其他元素

### 9. 搜索球队
- **实现**: 在日期栏和联赛标签之间加一个搜索输入框
- **逻辑**: 输入时过滤 `st.matches`，只显示包含搜索词的比赛
- **UI**: 简约搜索框，自带清除按钮

### 10. 深色/浅色主题切换
- **实现**: 页面右上角加一个 🌙/☀️ 切换按钮
- **逻辑**: 切换 `body` 的 `data-theme` 属性，CSS 变量控制颜色
- **存储**: localStorage 保存偏好

---

## 🟡 P2 — 核心功能

### 11. AI 智能选串（自动推荐最优组合）
- **前端**: 在 ⚽ 按钮旁边加一个"🤖 智能推荐"按钮
- **逻辑**: 
  1. 用户不选比赛，直接点"智能推荐"
  2. 前端自动取当前所有比赛（或置信度>60%的）
  3. 调 `/api/generate-combos?type=auto` （后端加 `type=auto` 支持）
  4. 后端自动枚举 2串1~6串1，返回命中率最高的那个
- **后端**: `api_generate_combos` 加 `if type == 'auto'`，枚举所有串关类型，返回最优

### 12. 模拟投注记录（虚拟2元验证AI）
- **实现**: localStorage 存 `k38_bet_history`
- **格式**: `[{date, combos: [{matches, prediction, hit_pct, odds}], virtual_profit}]`
- **展示**: 底部栏加"📊 战绩"入口，点开看到"本月推荐 30场·命中 20场·胜率 66.7%"

### 13. "今日精选"板块
- **实现**: 在比赛列表顶部加一个特殊卡片，展示当天置信度最高的3场比赛
- **样式**: 金色边框，比普通卡片高一点，显眼
- **数据**: 前端从 `st.matches` 里取 top 3 (按 confidence 排序)

### 14. "稳胆"标签
- **实现**: 当 `m.confidence >= 75` 时，在卡片右上角加 🟢稳胆 标签
- **样式**: 绿色小标签，和 🔥 标签同级显示

### 15. 推荐理由一句话摘要
- **实现**: 在卡片 AI 推荐行（`mc-rec`）后面加一行小字，如"主队近5场不败"
- **数据**: 当前没有这个数据，可以先显示"主队近期状态↑"或"客队伤停影响"
- **逻辑**: 根据 home_xg / away_xg 的差值简单判断，差值大 = "实力差距明显"

---

## 🔵 P3 — 数据/性能

### 16. 前端图片懒加载
- 球队 flag 如果换成图片，用 `loading="lazy"` 属性

### 17. gzip 压缩
- nginx 配置加 `gzip on; gzip_types text/html application/json;`

### 18. 静态资源 CDN
- 把 CSS/JS 从 HTML 里抽出来成独立文件，nginx 配强缓存

### 19. 新加坡服务器部署脚本
- 写一个 `deploy.sh` 脚本：git pull → pip install → systemctl restart

### 20. Docker 化
- 写 `Dockerfile` + `docker-compose.yml`
- 包含: Flask 服务 + nginx + SQLite

---

## 执行建议

```
第1个小时 → P0 (1-5) 修bug
第2-3个小时 → P1 (6-10) 快速体验提升
第4-6个小时 → P2 (11-15) 核心功能
剩下 → P3 (16-20) 性能/部署
```

每个任务做完跑一下 `curl https://boboji.beer/v84 | grep "波波鸡"` 确保没崩。

---

## 🔴 Round 2 — 线上验证反馈 (boboji.beer/v84)

### P1 - 功能缺陷

#### 21. fetch 超时保护
- **文件**: templates/v84-kimi-a.html (startAnim / auto recommend fetch)
- **问题**: generate-combos fetch 没有超时保护，串关计算慢时 UI 永久卡"加载中"
- **修复**: 加 AbortController + 15s timeout，超时后显示"计算超时，请减少场次"

#### 22. 搜索框默认显示
- **文件**: templates/v84-kimi-a.html
- **问题**: 搜索框默认隐藏，用户不知道有搜索功能
- **修复**: 去掉 display:none，默认显示搜索框；或至少加个搜索 icon 引导

#### 23. 搜索时联赛标签联动
- **文件**: templates/v84-kimi-a.html (searchInput handler)
- **问题**: 搜"巴西"但联赛标签还亮着，用户困惑
- **修复**: 搜索有内容时，清除当前联赛选中状态或只显示匹配到的联赛

### P2 - 兼容性问题

#### 24. 浅色主题 banner 文字颜色
- **文件**: templates/v84-kimi-a.html (light theme CSS)
- **问题**: 切换到浅色主题后，banner "波波鸡"白色文字看不清（白底白光）
- **修复**: `body[data-theme="light"] h1, body[data-theme="light"] .subtitle` 改深色

#### 25. 稳胆标签与AI推荐标签间距
- **文件**: templates/v84-kimi-a.html (.sure-tag CSS)
- **问题**: 稳胆标签和 AI 推荐标签堆叠在一起，间距不对
- **修复**: 调整 `.sure-tag` 和 `.mc-info` 的 flex 布局，加 gap 或 margin

#### 26. 底部操作栏遮挡最后一张卡片
- **文件**: templates/v84-kimi-a.html (.ml CSS)
- **问题**: 比赛列表滚动到底部，最后一个卡片被底部操作栏挡住一半
- **修复**: `.ml` 加 `padding-bottom` 等于底部栏高度

### P3 - 小优化

#### 27. fmtTime 函数提取到 render 外
- **文件**: templates/v84-kimi-a.html
- **问题**: fmtTime 在 render() 内部每次重新定义，性能浪费
- **修复**: 把 fmtTime 移到 render() 外面作为顶层函数

#### 28. 模拟投注记录清除按钮
- **文件**: templates/v84-kimi-a.html (stats overlay)
- **问题**: 模拟投注记录没有清除按钮，存了就删不掉
- **修复**: 已经有🗑清空按钮了，确认实际可用；如果不行就修 onclick

#### 29. AI智能选串 loading 状态
- **文件**: templates/v84-kimi-a.html (autoBtn click handler)
- **问题**: 点击后没有 loading 状态，用户不知道在算
- **修复**: 点击后按钮变灰 + 显示"计算中..."文字，完成后恢复

#### 30. localStorage try/catch 包裹
- **文件**: templates/v84-kimi-a.html (所有 localStorage 调用)
- **问题**: 隐私模式下 localStorage 可能抛异常导致页面崩溃
- **修复**: 统一用 safeGet/safeSet 包裹 localStorage 操作

