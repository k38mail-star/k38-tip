# ⚽ 波波机 — K38 Football AI Betting Recommender

**两元壹串🐔波波鸡** — 选几场足球比赛，AI帮你算串关

---

## 项目概述

波波机是一个AI足球推荐+串关分析工具。用户选择联赛和日期范围，AI（Poisson分布模型）预测每场比赛的胜负概率，用户勾选多场比赛后可一键生成串关组合分析。

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Flask (Python 3.10+) |
| 数据库 | SQLite (`/opt/k38-football/football.db`) |
| 预测模型 | Poisson 分布（自定义引擎） |
| 组合模拟 | Monte Carlo 蒙特卡洛模拟 |
| 赔率接口 | The Odds API（可降级） |
| 前端 | 纯HTML/CSS/JS（无框架） |
| 部署 | ECS Ubuntu 24.04, systemd, nginx |
| 域名 | tip.k38.ai → 7890端口 |

## 目录结构

```
/opt/k38-tip/
├── app.py                   # Flask主应用（API + 路由）
├── odds_service.py          # 赔率API封装（熔断降级）
├── engine/
│   ├── poisson.py           # Poisson分布预测模型
│   ├── monte_carlo.py       # 蒙特卡洛串关模拟
│   ├── kelly.py             # Kelly公式（未使用）
│   ├── walk_forward.py      # 回测（未使用）
│   └── stress_test.py       # 压力测试（未使用）
├── templates/
│   └── v84-kimi-a.html      # 前端页面（主版本）
├── static/                  # 静态文件
└── football_data/           # 数据脚本
```

## 设计逻辑

### 数据流

```
用户选联赛+日期 → Flask /api/candidates 
  → SQLite 查询未开始比赛 
  → Poisson 模型预测胜负概率 
  → 返回JSON（比赛+预测+置信度）
  → 前端渲染推荐列表

用户勾选比赛 → 点⚽智能组合 → /api/generate-combos
  → 取选中比赛ID 
  → 组合 C(n, 6) 所有6串1组合（最多5000组）
  → Poisson重新计算每组胜负概率
  → 蒙特卡洛模拟每组命中率
  → 排序返回Top组合
```

### 预测模型

使用 **Poisson 分布** 预测进球数：
1. `fit()` 从历史比赛计算每支球队的 **进攻强度** 和 **防守强度**
2. 对未开始的比赛，根据两队攻防系数预测预期进球数（xG）
3. 通过 Poisson 概率质量函数计算各种比分概率
4. 汇总为主胜/客胜/平局概率，取最高值作为推荐

### 串关算法

1. 用户选 N 场比赛（最多6串1）
2. 生成 C(N, 6) 种组合，上限5000组
3. 每组按 Poisson 预测概率计算 **组合命中率**（各场概率相乘）
4. 蒙特卡洛模拟 50000 次验证最终命中率
5. 按命中率排序返回 Top 组合

### 闪电信心分级

| 置信度 | 显示 | 含义 |
|--------|------|------|
| ≥90% | ⚡⚡⚡ 金色 | 极高信心 |
| ≥80% | ⚡⚡ 金色 | 高信心 |
| ≥60% | ⚡ 金色 | 中等信心 |
| <60% | 无 | 低信心，不推荐 |

### 熔断机制

- **赔率API熔断** `_odds_failed`：第一次外网API超时后，后续所有请求跳过赔率获取，不阻塞主流程
- **组合数上限** `MAX_COMBOS = 5000`：防止 C(30, 6)=593775 组合撑爆内存

## API 接口

| 路径 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/v84` | GET | — | 主页面（波波机前端） |
| `/api/candidates` | GET | date_from, date_to, leagues | 候选比赛列表+预测 |
| `/api/generate-combos` | GET | type(=2~6), ids(=ID&ids=ID...) | 串关组合分析 |
| `/api/leagues` | GET | — | 有数据的联赛列表 |
| `/predict` | GET | home, away, league_id | 单场预测API |

## 部署方式

```bash
# systemctl 管理
systemctl restart k38-tip     # 重启
systemctl status k38-tip      # 查看状态
journalctl -u k38-tip -n 20   # 查看日志

# 手动
kill $(lsof -t -i:7890)
python3 /opt/k38-tip/app.py
```

## 数据库

```
路径: /opt/k38-football/football.db
表: football_matches
字段: fixture_id, home_team, away_team, home_goals, away_goals,
      match_date, league_id, league_name, status, home_flag,
      away_flag, home_team_cn, away_team_cn, events...
关键过滤: status IN ('Not Started','NS') AND match_date >= '2026-01-01'
```

## 已知限制

- 赔率API从香港ECS访问较慢，已启用熔断+缓存
- 目前只世界杯(league_id=1)有2026年数据
- 最多6串1，最多20场比赛同时选择
- CSS星空背景为纯CSS绘制，不依赖外部图片

---

*波波机 — 看球必备 · 两元壹串波波鸡 🐔*
*⚠️ 合法体彩店购买 · 本站仅供看球娱乐参考*
