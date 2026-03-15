# Crayfish Grid Hunter (小龙虾网格猎人) v2.3.0

**Author**: joensmoon  
**Version**: 2.3.0  
**License**: MIT  
**Platform**: OpenClaw (Binance Agent Competition)

Crayfish Grid Hunter 是一款专为币安 Agent 比赛设计的 **AI 合约网格交易智能助手**。它完全适配 **OpenClaw** AI Agent 框架，实现了从市场双分类扫描、历史回测、等比网格参数生成到实时风险监控的全链路交易决策流程。

**核心亮点**：纯币安官方 Skill 组合，支持自然语言参数自定义，下载安装后即可在 OpenClaw 中立刻使用。

> **次新币定义**：在币安 USDS-M 永续合约市场上线不超过 **90 天**的合约。所有候选均来自币安官方 `fapi/v1/exchangeInfo` 白名单，**不包含任何未在币安合约市场上线的代币**。

---

## 🌟 What's New in v2.3.0

v2.3.0 修复了一个严重问题：AI Agent 在读取 SKILL.md 后不调用脚本而是自行生成数据。本次更新彻底解决了这个问题：

1. **新增完整 CLI 入口**：`grid_hunter_v5.py` 现在支持直接运行，支持所有参数通过命令行传递（`--mode cat-a/cat-b/all`、`--leverage`、`--contract-recent-days` 等）。
2. **强制执行指令**：SKILL.md 新增 5 条 Agent Behavior 强制规则，禁止 AI 自行生成数据。
3. **自然语言参数对照表**：SKILL.md 新增用户语言 → CLI 参数对照表，确保 AI 正确转换用户意图。

### v2.3.0 之前的功能（v2.1.0 已包含在内）

1. **安装体验极速升级**：新增一键安装脚本 `install.sh`，支持 `curl` 方式秒级安装，依赖管理完全透明。
2. **交互与展示全面进化**：
   * 引入动态进度条，长耗时任务状态一目了然。
   * 结果输出升级为**高亮 ASCII 数据表格**，参数对比更加直观。
   * 新增负资金费率标的高亮提示（💰），自动识别多头网格额外收益机会。
3. **参数优化建议引擎 (Parameter Advisor)**：新增 `param_advisor.py`，根据市场状态（横盘/趋势/高波动/突破）智能生成杠杆、网格数量及止损位的优化建议。
4. **API 与 Webhook 支持**：新增 `api_server.py`，提供完整的 REST API 接口（FastAPI），并支持将筛选结果通过 Webhook 推送至 Telegram/Discord/飞书。
5. **底层逻辑硬化 (Logic Hardening)**：
   * 强化了横盘筛选逻辑，将 ADX 作为硬性门槛（ADX ≥ 20 直接排除），彻底杜绝趋势行情混入次新币横盘池。
   * 修复了网格上轨低于当前价格、区间过窄导致利润不足等关键计算 Bug。
6. **文档体系重建**：新增 `docs/` 目录，包含 `QUICK_START.md`、`EXAMPLES.md`、`CONFIGURATION.md` 和 `ADVANCED.md`。

---

## 🚀 触发指令示例

直接在 OpenClaw 对话框中输入以下指令即可触发：

*   **“次新币网格”** → 自动筛选次新币横盘标的，进行回测并生成策略。
*   **“高波动套利”** → 自动筛选市值2亿-10亿的高换手妖币，进行回测并生成策略。
*   **"次新币网格，止损位设置在8%"** → 使用自定义止损参数执行筛选。
*   **“网格猎手”** → 执行完整的双分类筛选、回测并输出 Top 3 推荐。

---

## 📦 极速安装 (10秒搞定)

在 OpenClaw 环境中运行以下命令，一键安装本项目及所有依赖的官方 Skills：

```bash
# 推荐：使用一键安装脚本（自动安装核心与所有依赖）
curl -s https://raw.githubusercontent.com/joensmoon/Crayfish-Grid-Hunter/main/install.sh | bash

# 或使用 openclaw 命令手动安装
openclaw skills install crayfish-grid-hunter --with-deps
```

---

## 📚 完整文档体系

为了帮助不同阶段的用户快速上手，我们提供了完整的文档体系：

* [**QUICK_START.md**](docs/QUICK_START.md): 5分钟快速开始指南。
* [**EXAMPLES.md**](docs/EXAMPLES.md): 丰富的自然语言触发示例。
* [**CONFIGURATION.md**](docs/CONFIGURATION.md): 详细的参数配置说明。
* [**ADVANCED.md**](docs/ADVANCED.md): API 接口、Webhook 和回测集成的高级指南。
* [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md): 常见问题与故障排除指南。

---

## 🛠 项目结构

```text
/home/ubuntu/Crayfish-Grid-Hunter/
├── README.md               # 项目主文档
├── TROUBLESHOOTING.md      # 故障排除指南
├── TEST_RESULTS.md         # 最新版本测试报告 (v2.3.0)
├── install.sh              # 一键安装脚本
├── docs/                   # 完整文档体系
│   ├── QUICK_START.md
│   ├── EXAMPLES.md
│   ├── CONFIGURATION.md
│   └── ADVANCED.md
└── skills/
    └── crayfish-grid-hunter/
        ├── SKILL.md          # OpenClaw Skill 定义文件
        ├── CHANGELOG.md      # 版本变更日志
        ├── grid_hunter_v5.py # 核心筛选与策略引擎
        ├── monitor.py        # 实时监控模块
        ├── backtester.py     # 历史数据回测模块
        ├── progress.py       # [新增] 进度条与表格展示模块
        ├── param_advisor.py  # [新增] 参数优化建议引擎
        └── api_server.py     # [新增] API与Webhook服务
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

核心算法引擎、回测系统及所有 v2.3.0 新增模块均经过严格的本地单元测试。
当前测试套件包含 **162 个测试用例**（72 个原有测试 + 90 个 v2.0/v2.1 新增功能测试），测试结果 **100% 通过**。
详见 [TEST_RESULTS.md](TEST_RESULTS.md)。

---

## 作者与贡献

本项目由 **joensmoon** 独立开发，致力于为币安 Agent 比赛提供最专业的合约网格交易辅助工具。确保贡献者仅有一人。
