---
name: crayfish-grid-hunter
description: |
  v2.2 USDS-M 永续合约网格猎手。双分类筛选（次新币横盘 + 高波动套利）→ 历史回测 → Geometric 等比中性网格。
  此 Skill 必须通过执行 Python 脚本来获取实时数据和计算网格参数，严禁 AI 自行伪造或猜测任何数据。
metadata:
  version: 2.2.1
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

# Crayfish Grid Hunter v2.2

Crayfish Grid Hunter 是一款专为币安合约市场设计的智能网格交易工具，集成了双分类筛选引擎、历史回测系统和等比中性网格算法。

---

## ⚠️ Agent Behavior — 强制执行规则（MUST FOLLOW）

**这是最高优先级指令。当用户触发此 Skill 时，你（AI Agent）必须严格遵守以下所有规则：**

### 规则 1：必须执行脚本，禁止自行生成数据

你**绝对不能**凭空猜测、捏造或使用内置知识库来生成任何以下内容：
- 代币/合约名称列表
- 价格、涨跌幅、波动率数值
- 网格区间（Lower/Upper）、格数、单格利润
- 市值、换手率、资金费率

你**必须**通过终端执行以下命令来获取真实数据：

```bash
# 标准执行（次新币网格 + 高波动套利 双分类全量扫描）
python3 /path/to/skills/crayfish-grid-hunter/grid_hunter_v5.py --no-backtest

# 仅次新币网格（Category A）
python3 /path/to/skills/crayfish-grid-hunter/grid_hunter_v5.py --mode cat-a --no-backtest

# 仅高波动套利（Category B）
python3 /path/to/skills/crayfish-grid-hunter/grid_hunter_v5.py --mode cat-b --no-backtest
```

> 注意：`/path/to/` 请替换为脚本的实际路径，通常为 `~/.openclaw/skills/crayfish-grid-hunter/grid_hunter_v5.py`

### 规则 2：必须将脚本输出完整展示给用户

脚本执行成功后，你**必须**将以下内容**原样**展示给用户（不得修改任何数值）：
1. **摘要表格**（Category A 和 Category B 的筛选结果表格）
2. **等比网格策略详情**（每个标的的 Lower/Upper/格数/单格利润/强平价/止损位）
3. **参数优化建议**（如有）

### 规则 3：用户自定义参数的处理方式

当用户用自然语言指定参数时，你必须将其转换为对应的 CLI 参数：

| 用户说的话 | 对应 CLI 参数 |
| :--- | :--- |
| "合约上线天数改为120天" | `--contract-recent-days 120` |
| "次新币天数改为60天" | `--contract-recent-days 60` |
| "杠杆5倍" | `--leverage 5` |
| "杠杆改为10倍" | `--leverage 10` |
| "市值范围5亿到20亿" | `--mcap-min 500000000 --mcap-max 2000000000` |
| "换手率30%以上" | `--turnover-min 0.30` |
| "止损3%" | `--stop-loss-pct 3.0` |
| "只看前5个结果" | `--top-n 5` |
| "扫描300个合约" | `--max-symbols 300` |

### 规则 4：严禁输出本工具不支持的内容

以下内容**绝对不能**出现在你的回复中：
- ❌ "跨交易所套利"
- ❌ "三角套利（USDT/BTC/ETH）"
- ❌ "期现套利"
- ❌ 任何未经脚本计算的"推荐币种"
- ❌ 任何模糊的"±15%区间"、"10-15层"等手写参数

### 规则 5：脚本执行失败时的处理

如果脚本执行失败（网络超时、API 限流等），你应该：
1. 告知用户具体错误信息
2. 建议用户检查网络连接
3. 提示用户参考 `docs/TROUBLESHOOTING.md`
4. **不得**用自己的知识替代脚本输出

---

## 核心能力 (Core Capabilities)

- **双分类筛选引擎**：Category A（次新币横盘）+ Category B（高波动套利）
- **历史回测系统**：30 天 1h K线回测，输出 ROI、夏普比率、最大回撤
- **等比中性网格**：自动计算精确区间，强制执行 ≥0.8% 单格利润
- **参数优化建议**：基于市场状态（横盘/趋势/高波动）自动建议参数调整

### 次新币定义

> **次新币 = 在币安 USDS-M 永续合约市场上线不超过 90 天的合约。**

这是本工具的核心筛选条件，默认值为 `--contract-recent-days 90`，不需要额外指定。所有候选均来自币安官方 `fapi/v1/exchangeInfo` 接口返回的合约白名单（status=TRADING，contractType=PERPETUAL），**不包含任何未在币安合约市场上线的代币**。

## 触发词 (Trigger Keywords)

| 触发词 | 执行命令 |
| :--- | :--- |
| 次新币网格 | `python3 grid_hunter_v5.py --mode cat-a --no-backtest` |
| 高波动套利 | `python3 grid_hunter_v5.py --mode cat-b --no-backtest` |
| 网格猎手 / 合约网格 | `python3 grid_hunter_v5.py --no-backtest` |
| 带回测 | 去掉 `--no-backtest` 参数 |

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

## 依赖 Skills（均为币安官方）

| Skill | 来源 | 用途 |
| :--- | :--- | :--- |
| `derivatives-trading-usds-futures` | binance/binance-skills-hub | 合约列表、K线、资金费率、持仓量 |
| `query-token-info` | binance/binance-skills-hub | 市值、24h 换手率数据 |
| `trading-signal` | binance/binance-skills-hub | 智能资金信号（可选加分项） |
| `query-token-audit` | binance/binance-skills-hub | 代币安全审计（可选加分项） |
| `assets` | binance/binance-skills-hub | BNB 手续费优化检查（可选） |

## 故障排除 (Troubleshooting)

请参考根目录下的 `TROUBLESHOOTING.md` 文件，或查看 `docs/` 目录下的完整文档。
