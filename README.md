# Crayfish Grid Hunter (小龙虾网格猎人) v5.0

**Author**: joensmoon  
**Version**: 5.0.0  
**License**: MIT  
**Platform**: OpenClaw (Binance Agent Competition)

Crayfish Grid Hunter 是一款专为币安 Agent 比赛设计的 **AI 合约网格交易智能助手**。它完全适配 **OpenClaw** AI Agent 框架，实现了从市场双分类扫描、技术分析、等比网格参数生成到风险监控的全链路交易决策流程。

---

## 🌟 What's New in v5.0 (The Futures Update)

Version 5.0 是一次重大架构升级，全面转向 **币安 USDS-M 永续合约市场**，引入了双分类筛选模型和 Geometric 等比中性网格策略：

1. **双分类市场筛选 (Dual-Category Screening)**
   - **次新币横盘类 (Category A)**：筛选上市 60 天内、经历回调后进入横盘整理期的代币（ATR < 2%, BB-width < 5%, ADX < 20）。
   - **高波动套利类 (Category B)**：筛选高换手率、高真实波动率（RV > 15%/yr）且日内波幅在 5%-40% 的最佳套利标的。
2. **等比中性网格 (Geometric Neutral Grid)**
   - 采用等比数列 (`r^n = upper/lower`) 计算网格间距，确保每个价位的利润率完全一致，最适合高波动资产。
   - 严格控制单格净利润在 0.8%–1.2%（扣除手续费后），防止无效的高频交易。
3. **合约专属风险管理 (Futures Risk Management)**
   - **强平估算**：自动计算交叉保证金下的预估强平价格。
   - **5% 硬止损**：强制在网格下轨下方 5% 设置硬止损位。
   - **资金费率分析**：分析当前 Funding Rate，预估多头/空头网格的每日资金费率收益，并在极值时发出警告。
4. **增强版实时监控 (Enhanced Monitor)**
   - 新增了资金费率突变、价格逼近强平线等合约专属的 CRITICAL/HIGH 级监控报警。

---

## 工作流程

```text
用户: "帮我筛选一下合约市场的次新币和高波动币，做个等比网格"
    │
    ▼
Step 0: 双分类筛选 ── derivatives-trading-usds-futures (合约列表 + K线 + 资金费率)
    │                  Category A: 次新币横盘 | Category B: 高波动套利
    ▼
Step 1: 等比网格 ──── 20期布林带 + 3xATR 确定区间，计算等比比率 r 和单格利润
    │                  计算 5% 硬止损位、预估强平价、资金费率收益
    ▼
Step 2: 聪明钱验证 ── trading-signal (Smart Money 买入信号)
    │                  有BUY信号 → 评分+15
    ▼
Step 3: 安全审计 ──── query-token-audit (针对 BSC 链上代币)
    │                  DANGEROUS → 自动排除; SAFE → 评分+5
    ▼
Step 4: 费用优化 ──── assets (余额检查 + BNB燃烧抵扣) [可选，需API Key]
    │
    ▼
Step 5: 性能监控 ──── monitor.py (后台持续监控 PnL、资金费率、强平距离、API健康度)
```

---

## 项目结构

```text
crayfish-grid-hunter/
├── skills/
│   └── crayfish-grid-hunter/
│       ├── SKILL.md                      # 核心 Skill 定义（工作流与Prompt）
│       ├── grid_hunter_v5.py             # v5.0 核心算法引擎（双分类 + 等比网格）
│       ├── monitor.py                    # 性能监控与多级报警引擎（含合约专属监控）
│       ├── CHANGELOG.md                  # 版本更新记录
│       ├── LICENSE.md                    # MIT 许可证
│       └── references/                   # 技术参考文档
├── test_grid_hunter.py                   # 完整离线测试脚本（43项算法验证）
├── TEST_RESULTS.md                       # 测试报告
└── README.md                             # 本文档
```

---

## 快速开始 (OpenClaw)

此 Skill 完全符合 OpenClaw 规范，用户下载安装后即可**立刻使用**。

### 第一步：安装官方依赖 Skills

Crayfish Grid Hunter v5.0 依赖于币安官方的合约与 Web3 Skills：

```bash
# 请确保已安装 OpenClaw skills CLI
npm install -g skills

# 安装币安官方 Skills
skills add https://github.com/binance/binance-skills-hub -s derivatives-trading-usds-futures
skills add https://github.com/binance/binance-skills-hub -s trading-signal
```

### 第二步：安装 Crayfish Grid Hunter

```bash
skills add https://github.com/joensmoon/Crayfish-Grid-Hunter -s crayfish-grid-hunter
```

---

## 权限与认证

**无需 API 密钥**即可运行核心的市场筛选和网格参数计算功能。所有行情数据（K线、资金费率、24h Ticker）均通过币安公共端点获取。

只有当您需要让 Agent 自动检查账户余额或开启 BNB 抵扣时，才需要配置环境变量：
```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_secret_key"
```

---

## 作者与贡献

本项目由 **joensmoon** 独立开发，致力于为币安 Agent 比赛提供最专业的合约网格交易辅助工具。

---

## 许可证

本项目采用 **MIT** 许可证。
