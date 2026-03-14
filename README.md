# Crayfish Grid Hunter (小龙虾网格猎人) v1.0

**Author**: joensmoon  
**Version**: 1.0.0  
**License**: MIT  
**Platform**: OpenClaw (Binance Agent Competition)

Crayfish Grid Hunter 是一款专为币安 Agent 比赛设计的 **AI 合约网格交易智能助手**。它完全适配 **OpenClaw** AI Agent 框架，实现了从市场双分类扫描、历史回测、等比网格参数生成到实时风险监控的全链路交易决策流程。

**核心亮点**：纯币安官方 Skill 组合，支持自然语言参数自定义，新增 30 天历史回测系统，下载安装后即可在 OpenClaw 中立刻使用。

---

## 🌟 What's New in v1.0

1.  **历史回测系统 (Backtest Engine)**: 新增 `backtester.py`，支持对推荐标的进行最近 30 天的 1h K线回测，输出 ROI、夏普比率和最大回撤。
2.  **参数自定义 (User Customization)**: 支持通过自然语言指令自定义筛选阈值（如合约上线天数、市值范围、换手率要求）和网格参数（杠杆、止损位）。
3.  **实时监控增强 (Monitor Dashboard)**: `monitor.py` 新增实时仪表板、波动率 Regime 检测、自动网格调整建议及 Webhook 预警。
4.  **故障排除指南 (Troubleshooting)**: 新增 `TROUBLESHOOTING.md`，提供详细的安装、API 连接及策略逻辑故障排除说明。
5.  **纯官方数据源**: 严格遵守合规要求，**仅使用币安官方 Skills**，利用 `query-token-info` 获取市值数据，不依赖任何第三方插件。

---

## 🚀 触发指令示例

直接在 OpenClaw 对话框中输入以下指令即可触发：

*   **“次新币网格”** → 自动筛选次新币横盘标的，进行回测并生成策略。
*   **“高波动套利”** → 自动筛选市值2亿-10亿的高换手妖币，进行回测并生成策略。
*   **“次新币网格，合约上线天数改为60天，杠杆3倍”** → 使用自定义参数执行筛选。
*   **“网格猎手”** → 执行完整的双分类筛选、回测并输出 Top 3 推荐。

---

## 📦 极速安装 (10秒搞定)

在 OpenClaw 环境中运行以下命令，一键安装本项目及所有依赖的官方 Skills：

```bash
npx skills add https://github.com/joensmoon/Crayfish-Grid-Hunter
```

---

## 🛠 项目结构

```text
/home/ubuntu/Crayfish-Grid-Hunter/
├── README.md               # 项目主文档
├── TROUBLESHOOTING.md      # 故障排除指南
├── TEST_RESULTS.md         # 最新版本测试报告 (v1.0.0)
├── .gitignore              # 忽略文件配置
└── skills/
    └── crayfish-grid-hunter/
        ├── SKILL.md        # OpenClaw Skill 定义文件
        ├── CHANGELOG.md    # 版本变更日志
        ├── grid_hunter_v5.py # v1.0 核心筛选与策略引擎
        ├── monitor.py      # v1.0 增强版实时监控模块
        └── backtester.py   # v1.0 新增历史数据回测模块
```

## 依赖的官方 Skills (无第三方)

| Skill | 来源 | 用途 |
| :--- | :--- | :--- |
| `derivatives-trading-usds-futures` | `binance/` | 获取永续合约列表、K线数据、资金费率 |
| `query-token-info` | `binance-web3/` | **获取市值 (Market Cap) 计算真实换手率** |
| `trading-signal` | `binance-web3/` | 获取 Smart Money 信号加分 |
| `query-token-audit` | `binance-web3/` | 获取安全审计结果加分 |
| `assets` | `binance/` | 账户余额与手续费优化 |

---

## 测试覆盖率

核心算法引擎经过 85 项严格的本地单元测试（包含 v1.0 新增的回测逻辑、参数校验、实时仪表板渲染等），测试结果 100% 通过。详见 [TEST_RESULTS.md](TEST_RESULTS.md)。

---

## 作者与贡献

本项目由 **joensmoon** 独立开发，致力于为币安 Agent 比赛提供最专业的合约网格交易辅助工具。仅有一个贡献者。
