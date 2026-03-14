# Crayfish Grid Hunter (小龙虾网格猎人) v4.2.0

Crayfish Grid Hunter 是一款专为币安 Agent 比赛设计的 **AI 网格交易智能助手**。它完全适配 **OpenClaw** AI Agent 框架，深度集成了 **5 个币安官方 Skill**，实现了从市场扫描、技术分析、聪明钱验证、安全审计到费用优化的**全链路网格交易决策流程**。

---

## 核心亮点：功能分级设计

Crayfish Grid Hunter 采用了**功能分级设计**，旨在降低普通用户的使用门槛，同时为高阶用户提供增强功能。

### 1. 核心功能（免 API 密钥，即装即用）
基于币安官方的公共 API，无需配置 `BINANCE_API_KEY` 即可运行：
*   **智能筛选**：扫描过去 14 天波动率高且趋势平稳（横盘）的币种。
*   **动态区间**：基于布林带和 72 小时支撑/压力位生成网格区间。
*   **聪明钱验证**：交叉验证候选币种是否有 Smart Money 买入信号。
*   **安全审计**：推荐前自动检测蜜罐、Rug Pull、异常税率等风险。

### 2. 增强功能（需 API 密钥）
当用户配置了 `BINANCE_API_KEY` 后，将激活以下高级功能：
*   **费用优化**：检查并建议开启 BNB 抵扣手续费，最大化网格收益。
*   **余额检查**：自动核对账户余额，确保有足够资金执行推荐的网格策略。

---

## 工作流程

```text
用户: "帮我找个适合做网格的币"
    │
    ▼
Step 1: 市场扫描 ──── crypto-market-rank (获取热门币种排名)
    │
    ▼
Step 2: 技术分析 ──── spot (K线数据 → ATR/RSI/布林带/趋势斜率)
    │                  筛选: 波动率>3%, |斜率|<2%, RSI 25-75
    ▼
Step 3: 聪明钱验证 ── trading-signal (Smart Money 买入/卖出信号)
    │                  有BUY信号 → 评分+15, 标记"聪明钱支持"
    ▼
Step 4: 安全审计 ──── query-token-audit (蜜罐/Rug Pull/税率检测)
    │                  DANGEROUS → 自动排除; SAFE → 评分+5
    ▼
Step 5: 费用优化 ──── assets (余额检查 + BNB燃烧抵扣) [可选，需API Key]
    │
    ▼
Step 6: 生成推荐 ──── 综合评分(0-115), 输出完整建议
    │
    ▼
Step 7: 突破预警 ──── 持续监控, 量价异动时提醒用户
```

---

## 项目结构

```text
crayfish-grid-hunter/
├── skills/
│   └── crayfish-grid-hunter/
│       ├── SKILL.md                      # 核心 Skill 定义（7步工作流）
│       ├── CHANGELOG.md                  # 版本更新记录
│       ├── LICENSE.md                    # MIT 许可证
│       └── references/                   # 技术参考文档
│           ├── api_usage.md              # 5个Skill的API调用指南
│           └── technical_indicators.md   # 技术指标 + 评分体系
├── test_grid_hunter.py                   # 完整测试脚本（10个测试用例）
├── TEST_RESULTS.md                       # 测试报告
└── README.md                             # 本文档
```

---

## 快速开始 (OpenClaw)

### 第一步：一键安装所有依赖 Skills

Crayfish Grid Hunter 集成了 5 个币安官方 Skill。运行以下命令一次性安装全部依赖：

```bash
npx skills add https://github.com/binance/binance-skills-hub \
  --skill spot \
  --skill crypto-market-rank \
  --skill trading-signal \
  --skill query-token-audit \
  --skill assets \
  -a openclaw -y
```

### 第二步：安装 Crayfish Grid Hunter Skill

```bash
npx skills add https://github.com/joensmoon/Crayfish-Grid-Hunter -a openclaw -y
```

### 第三步：验证安装

安装完成后，确认 `skills/` 目录结构如下：

```text
skills/
├── spot/                    # [必需] 币安现货行情与交易
├── crypto-market-rank/      # [必需] 市场排名与热门代币
├── trading-signal/          # [可选] 聪明钱信号
├── query-token-audit/       # [可选] 代币安全审计
├── assets/                  # [可选] 资产管理与BNB燃烧
└── crayfish-grid-hunter/    # Crayfish Grid Hunter 主 Skill
```

---

## 作者与贡献

本项目由 **joensmoon** 独立开发，致力于为币安 Agent 比赛提供最专业的网格交易辅助工具。

---

## 许可证

本项目采用 **MIT** 许可证。
