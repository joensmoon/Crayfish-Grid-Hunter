---
name: crayfish-grid-hunter
description: |
  v5.2 USDS-M 永续合约网格猎手。双分类筛选（次新币横盘 + 高波动套利）→ Geometric 等比中性网格 → 实时监控。
  纯币安官方 Skill 组合，无需第三方 API Key，下载即用。
metadata:
  version: 5.2.0
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

# Crayfish Grid Hunter v5.2

USDS-M 永续合约专用网格猎手。从全市场合约中自动筛选标的，生成 Geometric 等比中性网格策略，并持续监控风险。

## Trigger Conditions

当用户消息包含以下任一关键词时，激活此 Skill：

| 触发词 | 对应动作 |
| :--- | :--- |
| 次新币网格 | 执行 Category A 筛选 → 生成网格策略 |
| 高波动套利 | 执行 Category B 筛选 → 生成网格策略 |
| 网格猎手 | 执行双分类全量筛选 → 生成网格策略 |
| 合约网格 | 执行双分类全量筛选 → 生成网格策略 |
| 网格交易策略 | 针对指定币种生成 Geometric 中性网格 |
| Geometric 网格 | 针对指定币种生成 Geometric 中性网格 |
| 筛选合约标的 | 执行双分类全量筛选 |

---

## Dependencies (Official Skills Only)

```bash
npx skills add https://github.com/binance/binance-skills-hub \
  --skill derivatives-trading-usds-futures \
  --skill query-token-info \
  --skill trading-signal \
  --skill query-token-audit \
  --skill assets \
  -a openclaw -y
```

| Skill | Source | Purpose |
| :--- | :--- | :--- |
| `derivatives-trading-usds-futures` | `binance/` | 合约列表、K线、资金费率、未平仓量 |
| `query-token-info` | `binance-web3/` | **市值（Market Cap）、换手率、代币信息** |
| `trading-signal` | `binance-web3/` | Smart Money 信号加分 |
| `query-token-audit` | `binance-web3/` | 安全审计加分 |
| `assets` | `binance/` | 账户余额、手续费优化 |

---

## Workflow

### Step 0: Load All USDS-M Perpetual Contracts

```
GET /fapi/v1/exchangeInfo
Skill: derivatives-trading-usds-futures
```

Filter: `contractType == "PERPETUAL"` AND `quoteAsset == "USDT"` AND `status == "TRADING"`.

Extract for each symbol:
- `symbol`, `baseAsset`, `onboardDate` (contract listing timestamp)
- `pricePrecision`, `quantityPrecision`, `tickSize`, `stepSize`

Then fetch all 24hr tickers in one call:

```
GET /fapi/v1/ticker/24hr
```

Sort by `quoteVolume` descending, take top 200 for analysis.

---

### Step 1: Fetch Technical Data

For each of the top 200 symbols:

```
GET /fapi/v1/klines?symbol={symbol}&interval=1d&limit=30
GET /fapi/v1/premiumIndex?symbol={symbol}
GET /fapi/v1/openInterest?symbol={symbol}
```

Compute from 30 daily klines:

| Indicator | Formula | Purpose |
| :--- | :--- | :--- |
| ATR(14) % | `mean(TR[-14:]) / close * 100` | Volatility measurement |
| BB Width % | `4 * std(close[-20:]) / sma(close[-20:]) * 100` | Range width (standard 20-period) |
| ADX(14) | Wilder's DI+/DI-/DX smoothing | Trend strength |
| RV % | `std(log_returns) * sqrt(365) * 100` | Annualized realized volatility |
| Volume Shrinkage | `volume[-1] / mean(volume[-8:-1])` | Current vs 7-day average |
| Support | `min(lows[-20:])` | 20-period swing low |
| Resistance | `max(highs[-20:])` | 20-period swing high |

---

### Step 2: Fetch Market Cap Data

For **Category B** screening, call the official `query-token-info` skill:

```
GET https://web3.binance.com/bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search
    ?keyword={baseAsset}&orderBy=volume24h
Skill: query-token-info
Headers: User-Agent: binance-web3/1.0 (Skill)
```

Extract: `marketCap` (USD), `volume24h` (USD).

Compute **real turnover rate**: `turnover = futures_quoteVolume_24h / marketCap`.

---

### Step 3: Category A — 次新币横盘类

**Definition**: 近 90 天内新上线合约的币种，已经历首波回调，目前成交量萎缩并在窄幅箱体横盘。

| 筛选条件 | 阈值 | 数据来源 |
| :--- | :--- | :--- |
| 合约上线时间 | `onboardDate` 距今 ≤ 90 天 | `exchangeInfo` |
| 成交量萎缩 | 24h Volume < 7日均量的 50% | `klines` (volume) |
| 横盘确认（满足任一） | ATR(14) < 2% 或 BB宽 < 5% 或 ADX < 20 | `klines` 计算 |

**Scoring (0–100)**:

| Component | Max Points | Formula |
| :--- | :--- | :--- |
| ATR 横盘强度 | 25 | `(2.0 - ATR) / 2.0 * 25` |
| BB 窄幅强度 | 25 | `(5.0 - BB_width) / 5.0 * 25` |
| ADX 无趋势 | 20 | `(20 - ADX) / 20 * 20` |
| 成交量萎缩 | 15 | `(0.5 - vol_ratio) / 0.5 * 15` |
| 上线时间新 | 15 | `(90 - age_days) / 90 * 15` |

Output top 3 by score.

---

### Step 4: Category B — 高波动套利类

**Definition**: 市值 $2亿–$10亿、24h 换手率 > 50%、实现波动率处于高位的"妖币"。

| 筛选条件 | 阈值 | 数据来源 |
| :--- | :--- | :--- |
| 市值 | $200M – $1,000M | `query-token-info` |
| 24h 换手率 | > 50% (`quoteVolume / marketCap`) | `ticker` + `query-token-info` |
| 实现波动率 | RV > 15% annualized | `klines` log returns |
| 量能确认 | 24h quoteVolume > $10M | `ticker` |

**Scoring (0–100)**:

| Component | Max Points | Formula |
| :--- | :--- | :--- |
| 实现波动率 | 30 | `min(RV / 50 * 30, 30)` |
| 换手率 | 25 | `min(turnover / 2.0 * 25, 25)` |
| 最优24h波动 | 25 | 15%–25% range = max, penalty outside |
| 量能强度 | 20 | `min(quoteVol / $100M * 20, 20)` |

Output top 3 by score.

---

### Step 5: Generate Geometric Neutral Grid

For each screened symbol (volatility 15%–25% preferred):

**Grid Type**: Geometric (equal-ratio) — each grid level is a fixed ratio `r` apart.

**Direction**: Neutral — no initial position, buy below current price, sell above.

**Grid Range**:
```
lower = max(BB_lower, support, price - 3×ATR)
upper = min(BB_upper, resistance, price + 3×ATR)
Minimum range: ±5% from current price
```

**Grid Count** (based on 24h volatility):

| 24h Volatility | Grid Count |
| :--- | :--- |
| ≥ 25% | 50 |
| 15%–25% | 40 |
| 8%–15% | 30 |
| < 8% | 20 |

**Geometric Ratio**:
```python
r = (upper / lower) ** (1 / grid_count)
profit_per_grid = r - 1 - 2 * 0.0004   # Deduct 0.04% maker fee per side
```

**Minimum Profit Enforcement**: If `profit_per_grid < 0.8%`, reduce `grid_count` until `profit ≥ 0.8%`.

**Risk Control**:
```python
stop_loss = lower * 0.95                # 5% hard stop below lower bound
liquidation_price = lower * (1 - 1/leverage + 0.004)  # Estimated liquidation
max_position = account_balance * 0.08   # Max 8% account exposure
```

**Funding Alpha**:
```python
if funding_rate < 0 and grid_direction == "long":
    daily_yield = abs(funding_rate) * 3 * 100  # 3 settlements per day
    alert(INFO, f"Negative funding: long grid earns +{daily_yield:.3f}%/day")
```

---

### Step 6: Smart Money & Security Bonus

**Optional enhancement** — adds bonus points to grid score:

```
GET trading-signal → Smart Money BUY signal → +15 points
GET query-token-audit → SAFE result → +5 points
```

---

### Step 7: Real-Time Monitoring

After grid deployment, run continuous monitoring via `monitor.py`:

#### 7.1 Grid Performance

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| PnL ≤ −5% | **CRITICAL** | Recommend closing grid |
| PnL ≤ −3% | **HIGH** | Warn of underperformance |
| Fill rate ≤ 5% | **CRITICAL** | Grid may be too wide |
| Fill rate ≤ 20% | **MEDIUM** | Consider tightening grid |

#### 7.2 Market Condition

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| Price within 3% of grid boundary | **CRITICAL** | Warn of imminent breakout |
| Price exits grid range entirely | **CRITICAL** | Grid is now inactive |
| Volume ≥ 2.5× 24h average | **CRITICAL** | Breakout signal — review |

#### 7.3 Risk Management (Futures-Specific)

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| Price within 2% of stop-loss | **CRITICAL** | Immediate stop-loss warning |
| Price within 10% of liquidation | **CRITICAL** | Reduce leverage or add margin |
| Drawdown from peak ≥ 8% | **CRITICAL** | Recommend emergency exit |
| Funding rate turns positive (>0.1%) | **HIGH** | Long grid now paying funding |

#### 7.4 API Health

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| Average latency ≥ 3000ms | **HIGH** | Degraded data freshness |
| Error rate ≥ 20% | **HIGH** | Unreliable data |

---

### Step 8: Output Format

**Screening Output (Step 3–4)**:

```
【次新币横盘类 — Category A】
  1. XXXUSDT  当前价 $xx.xx  24h波动率 xx.xx%  支撑 $xx.xx  压力 $xx.xx
     → 合约上线30天; 成交量萎缩至35%; ATR=1.5%, BB宽=3.2%, ADX=15.3
  2. ...
  3. ...

【高波动套利类 — Category B】
  1. YYYUSDT  当前价 $xx.xx  24h波动率 xx.xx%  支撑 $xx.xx  压力 $xx.xx
     → 市值$500M; 换手率85%; RV=22.5%/yr; 24h波动=18.3%
  2. ...
  3. ...
```

**Strategy Output (Step 5)**:

```
  针对 XXXUSDT：
  策略类型       : 合约中性网格（Neutral）
  网格类型       : Geometric 等比
  当前价格       : $xx.xxxx
  网格区间       : $xx.xxxx — $xx.xxxx
  网格数量       : 40 grids
  网格比率(r)    : 1.xxxxxx
  单格利润率     : 0.xx%（扣 0.04% 手续费后）
  杠杆倍数       : 5×
  5%硬止损位     : $xx.xxxx（下轨下方5%）
  强平价估算     : $xx.xxxx
  24h波动率      : xx.xx%
  支撑 / 压力    : $xx.xxxx / $xx.xxxx
  市值           : $xxxM  换手率: xx.x%
  Funding提醒    : funding rate -0.0120%，多头网格每日预期收益 +0.036%
  网格评分       : xx/100
```

---

## Authentication

This skill **does not require** a Binance API key for its core screening and grid calculation functions. All public endpoints are accessible without authentication.

An API key is required only for account-specific features (balance checks, fee optimization, order placement):

```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_secret_key"
```

---

## User-Agent Headers

```
derivatives-trading-usds-futures: crayfish-grid-hunter/5.2.0 (derivatives-trading-usds-futures Skill)
query-token-info / trading-signal / query-token-audit: crayfish-grid-hunter/5.2.0 (binance-web3 Skill)
```

---

## Grid Score Reference

| Component | Max Points | Category | Criteria |
| :--- | :--- | :--- | :--- |
| ATR 横盘强度 | 25 | A | ATR < 2% |
| BB 窄幅强度 | 25 | A | BB width < 5% |
| ADX 无趋势 | 20 | A | ADX < 20 |
| 成交量萎缩 | 15 | A | Vol < 50% of 7d avg |
| 上线时间新 | 15 | A | Newer = higher |
| 实现波动率 | 30 | B | Higher RV = higher |
| 换手率 | 25 | B | Higher turnover = higher |
| 最优24h波动 | 25 | B | 15%–25% = max |
| 量能强度 | 20 | B | Higher volume = higher |
| Smart Money BUY | +15 | Both | Active BUY signal |
| Security SAFE | +5 | Both | SAFE audit result |
