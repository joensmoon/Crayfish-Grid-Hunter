---
name: crayfish-grid-hunter
description: |
  v2.0 USDS-M 永续合约网格猎手。双分类筛选（次新币横盘 + 高波动套利）→ 历史回测 → Geometric 等比中性网格 → 实时监控。
  新增：进度条、表格化结果展示、参数优化建议引擎、REST API、Webhook支持、丰富文档。纯币安官方 Skill 组合，下载即用。
metadata:
  version: 2.0.0
  author: joensmoon
  openclaw:
    requires:
      - derivatives-trading-usds-futures
      - query-token-info
      - trading-signal
      - query-token-audit
      - assets
    optionalEnv:
      - BINANCE_API_KEY
      - BINANCE_API_SECRET
license: MIT
---

# Crayfish Grid Hunter v1.0

Crayfish Grid Hunter 是一款专为币安合约市场设计的智能网格交易工具。它集成了双分类筛选引擎、历史回测系统、等比中性网格算法以及实时性能监控。

## 核心能力 (Core Capabilities)

*   **双分类筛选引擎 (Dual-Category Screening)**:
    *   **次新币横盘类 (Category A)**: 筛选合约上线 ≤90 天、成交量萎缩并在窄幅箱体横盘的标的。
    *   **高波动套利类 (Category B)**: 筛选市值 $2亿-$10亿、24h 换手率 >50% 且实现波动率（RV）处于高位的“妖币”。
*   **历史回测系统 (Backtesting Engine)**: 支持对推荐标的进行 30 天历史数据回测，评估 ROI、夏普比率和最大回撤。
*   **等比中性网格 (Geometric Neutral Grid)**: 采用等比网格算法，应对高波动资产，自动计算强平价并强制执行 ≥0.8% 的单格利润率。
*   **实时性能监控 (Real-time Monitoring)**: 监控 PnL、波动率变化、强平风险及资金费率，支持 Webhook 预警。
*   **参数自定义 (Customizable Parameters)**: 支持通过自然语言指令自定义筛选阈值、杠杆倍数、止损位等参数。

## 触发词 (Trigger Keywords)

| 触发词 | 对应动作 |
| :--- | :--- |
| 次新币网格 | 执行 Category A 筛选 → 回测 → 生成策略 |
| 高波动套利 | 执行 Category B 筛选 → 回测 → 生成策略 |
| 网格猎手 / 合约网格 | 执行全量筛选 → 回测 → 生成策略 |
| 自定义参数示例 | "次新币网格，合约上线天数改为60天，杠杆3倍" |

## 安装 (Installation)

### 一键安装 (推荐)
```bash
curl -s https://raw.githubusercontent.com/joensmoon/Crayfish-Grid-Hunter/main/install.sh | bash
```

### 手动安装
```bash
# 安装本 skill
npx skills add https://github.com/joensmoon/Crayfish-Grid-Hunter -a openclaw -y

# 安装官方依赖 Skills
npx skills add https://github.com/binance/binance-skills-hub \
  --skill derivatives-trading-usds-futures \
  --skill query-token-info \
  --skill trading-signal \
  --skill query-token-audit \
  --skill assets \
  -a openclaw -y
```

### 可选依赖 (API 服务器)
```bash
pip install fastapi uvicorn  # 仅当需要 REST API 接口时
```
## 工作流 (Workflow v2.0)

### Step 1: 市场扫描与筛选
调用 `grid_hunter_v5.py` 对全市场 USDS-M 永续合约进行扫描。支持 `UserConfig` 参数自定义。
**v2.0 新增**: 实时进度条显示扫描进度，每步均有状态反馈。

### Step 2: 数据采集与指标计算
*   获取 `onboardDate`、K线、市値及换手率数据。
*   计算 ATR(14)、…20期布林带、ADX(14) 和年化实现波动率 (RV)。

### Step 3: 历史回测 (Backtest)
调用 `backtester.py` 对推荐标的进行最近 30 天的 1h K线回测，输出详细回测报告。

### Step 4: 策略生成
生成 Geometric (等比) 中性网格策略，计算网格区间、密度、强平价及 5% 硬止损位。

### Step 5: 实时监控 (Monitor)
启动 `monitor.py` 开启实时监控，提供仪表板、波动率检测及 Webhook 预警。

## 故障排除 (Troubleshooting)

请参考根目录下的 `TROUBLESHOOTING.md` 文件解决常见安装与运行问题。

## v2.0 新增模块

| 模块 | 功能 |
| :--- | :--- |
| `progress.py` | 进度条、表格格式化、友好错误信息 |
| `param_advisor.py` | 参数优化建议引擎、市场状态检测 |
| `api_server.py` | REST API 接口、Webhook 支持 |
| `docs/QUICK_START.md` | 5分钟快速开始 |
| `docs/EXAMPLES.md` | 丰富使用示例 |
| `docs/CONFIGURATION.md` | 详细配置说明 |
| `docs/ADVANCED.md` | 高级使用指南 |
| `install.sh` | 一键安装脚本 |
