# 📋 波波机（k38-tip）修复任务

## 项目位置

**本地路径：** `~/.openclaw/workspace/k38-tip-src/`
**GitHub 仓库：** https://github.com/k38mail-star/k38-tip.git

## 项目简介

波波机是一个AI足球推荐+串关分析工具。Flask 后端 + Poisson分布预测引擎 + 纯HTML/CSS/JS前端。
部署目标：新加坡 ECS (47.82.162.85)，systemd + nginx，域名 tip.k38.ai。

## 代码结构

```
k38-tip-src/
├── app.py                   # Flask主应用（路由 + 预测 + 串关API）
├── odds_service.py          # 赔率API封装（熔断降级）
├── engine/
│   ├── poisson.py           # Poisson分布预测模型（核心引擎）
│   ├── monte_carlo.py       # 蒙特卡洛串关模拟
│   ├── kelly.py             # 🔴 未使用 — 可清理
│   ├── walk_forward.py      # 🔴 未使用 — 可清理
│   └── stress_test.py       # 🔴 未使用 — 可清理
├── templates/
│   └── v84-kimi-a.html      # 前端主页面（活跃使用）
│   └── v2.html ~ v84.html   # 🔴 14个模板大部分废弃
├── collector/
│   └── odds.py              # 赔率收集
└── README.md                # 设计文档
```

## 🔴 需要修复的问题（按优先级）

### P0 — 熔断永不重置（关键修复）
**文件：** `app.py` 全局变量 `_odds_failed`
**问题：** 一旦赔率API超时，`_odds_failed` 永久设为 `True`，后续所有请求不再尝试获取赔率（只能靠重启恢复）。
**方案建议：**
- 改成带时间衰减的熔断（如 300秒后自动重置）
- 或按失败次数加权（连续失败3次才熔断，5分钟后尝试恢复）

### P1 — 三个未使用模块被 import
**文件：** `engine/kelly.py`, `engine/walk_forward.py`, `engine/stress_test.py`
**问题：** 被 `__pycache__` 中还保留着编译缓存，`app.py` 中的 import 链没有引用它们，但编译时会被加载。
**方案建议：** 删掉这三个文件（或在文件首行加 `# DEPRECATED` 标记）

### P1 — 模板爆炸
**文件：** `templates/` 目录下有14个HTML文件
**问题：** 只有 `v84-kimi-a.html` 是实际使用的版本。`v2.html`~`v5.html`、`v83.html`、`v84-ds.html`、`v84-codex.html`、`v84-kimi.html`、`v84-kimi-b.html`、`v84-kimi-c.html`、`v81-home.html`、`v84.html`、`index.html` 全部是历史版本。
**方案建议：**
- 删掉废弃模板，只保留 `v84-kimi-a.html`
- `app.py` 中对应的废弃路由也一并清理（注意别删 `app.py` 里的 v84 功能路由）

### P2 — `get_stats_for_team()` 死代码
**文件：** `app.py` 第66-84行
**问题：** 定义了函数但没有任何地方调用它。
**方案建议：** 删掉这个函数，或者把它挂到某个API接口上。

### P2 — 回测脚本已就绪但未集成
**文件：** `engine/walk_forward.py`, `engine/stress_test.py`
**问题：** 回测框架写好了但没接入 Flask。Poisson模型预测准确率无从验证。
**方案建议：**
- 可加一个 `/api/backtest` 路由，调用 walk_forward 跑历史数据回测
- 或者先注释掉，保留代码结构

## ✅ 不要动的东西

- `engine/poisson.py` — 核心预测模型，工作正常
- `engine/monte_carlo.py` — 蒙特卡洛模拟，工作正常
- `templates/v84-kimi-a.html` — 前端UI，功能完整
- `app.py` 中 `build_candidate_results()` 和 `api_generate_combos()` — 主业务流程
- `collector/odds.py` — 赔率采集逻辑

## 🚀 部署相关

部署完成后会上传到新加坡 ECS（47.82.162.85）：
```bash
# systemd 服务名: k38-tip
# 端口: 7890
# 域名: tip.k38.ai → nginx 反代到 127.0.0.1:7890
```

## 完成标准

1. ✅ 熔断机制修复（带时间衰减或次数加权）
2. ✅ 未使用的模板和文件清理
3. ✅ 死代码删除或接入
4. ✅ 代码自检通过（`python3 app.py` 能正常启动，`curl http://127.0.0.1:7890/v84` 返回页面）
5. ✅ git commit + push
