# Crayfish Grid Hunter (小龙虾网格猎人) v5.2

**Author**: joensmoon  
**Version**: 5.2.0  
**License**: MIT  
**Platform**: OpenClaw (Binance Agent Competition)

Crayfish Grid Hunter 是一款专为币安 Agent 比赛设计的 **AI 合约网格交易智能助手**。它完全适配 **OpenClaw** AI Agent 框架，实现了从市场双分类扫描、技术分析、等比网格参数生成到风险监控的全链路交易决策流程。

**核心亮点**：纯币安官方 Skill 组合，无需任何第三方 API Key，下载安装后即可在 OpenClaw 中立刻使用。

---

## 🌟 What's New in v5.2 (完美适配比赛 Prompt)

1. **纯官方数据源**：严格遵守合规要求，**仅使用币安官方 Skills**，利用 `query-token-info` 获取市值（Market Cap）计算真实换手率，**不依赖 CoinAnk 等第三方插件**。
2. **双分类全量筛选**：
   - **次新币横盘类 (Category A)**：自动寻找近 90 天内新上线合约、成交量萎缩至均量 50% 以下、且处于窄幅箱体横盘（ATR < 2% / BB宽 < 5%）的标的。
   - **高波动套利类 (Category B)**：自动寻找市值在 $2亿-$10亿之间、24h 换手率 > 50%、且实现波动率（RV）极高的“妖币”。
3. **Geometric 等比中性网格**：
   - 强制使用等比网格（Geometric），以应对高波动率资产。
   - 动态调整网格密度，精确控制单格利润率在 **0.8% - 1.2%** 之间（扣除 0.04% 手续费后）。
   - 自动计算 5% 硬止损位与强平价格。
4. **Funding 阿尔法提醒**：实时监控资金费率，当费率为负且开多头网格时，自动计算并提醒预期的费率收益。

---

## 🚀 触发指令示例

直接在 OpenClaw 对话框中输入以下极简指令即可触发：

- **“次新币网格”** → 自动筛选次新币横盘标的，并生成网格策略。
- **“高波动套利”** → 自动筛选市值2亿-10亿的高换手妖币，并生成网格策略。
- **“网格猎手”** → 执行完整的双分类筛选，并输出每个分类的 Top 3 推荐及策略参数。

---

## 📦 极速安装 (10秒搞定)

在 OpenClaw 环境中运行以下命令，一键安装本项目及所有依赖的官方 Skills：

```bash
npx skills add https://github.com/binance/binance-skills-hub \
  --skill derivatives-trading-usds-futures \
  --skill query-token-info \
  --skill trading-signal \
  --skill query-token-audit \
  --skill assets \
  -a openclaw -y

npx skills add https://github.com/joensmoon/Crayfish-Grid-Hunter \
  --skill crayfish-grid-hunter \
  -a openclaw -y
```

---

## 🛠 依赖的官方 Skills (无第三方)

| Skill | 来源 | 用途 |
| :--- | :--- | :--- |
| `derivatives-trading-usds-futures` | `binance/` | 获取永续合约列表、K线数据、资金费率 |
| `query-token-info` | `binance-web3/` | **获取市值 (Market Cap) 计算真实换手率** |
| `trading-signal` | `binance-web3/` | 获取 Smart Money 信号加分 |
| `query-token-audit` | `binance-web3/` | 获取安全审计结果加分 |
| `assets` | `binance/` | 账户余额与手续费优化（仅下单时需要 API Key） |

---

## 权限与认证

**无需 API 密钥**即可运行核心的市场筛选和网格参数计算功能。所有行情数据均通过币安公共端点获取。

只有当您需要让 Agent 自动检查账户余额或开启 BNB 抵扣时，才需要配置环境变量：
```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_secret_key"
```

---

## 测试覆盖率

核心算法引擎经过 72 项严格的本地单元测试（包含 90 天次新边界、等比比率精度、最低利润强制执行等），测试结果 100% 通过。详见 [TEST_RESULTS.md](TEST_RESULTS.md)。

---

## 作者与贡献

本项目由 **joensmoon** 独立开发，致力于为币安 Agent 比赛提供最专业的合约网格交易辅助工具。仅有一个贡献者。
