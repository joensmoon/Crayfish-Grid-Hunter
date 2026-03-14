---
name: crayfish-grid-hunter
description: "Crayfish Grid Hunter is an AI-powered grid trading assistant for Binance USDS-M Perpetual Futures. It performs dual-category screening — Category A: Recent Listings in sideways consolidation (次新币横盘类), Category B: High-Volatility Arbitrage candidates (高波动套利类) — then generates Geometric Neutral Grid strategies with precise per-grid profit control (0.8%–1.2% after fees), liquidation price calculation, 5% hard stop-loss, and funding rate yield alerts. Use this skill when users ask about futures grid trading, coin screening for grid strategies, Geometric grid parameters, or 'which futures coin is good for grid trading'."
metadata: {"version":"5.0.0","author":"joensmoon","openclaw":{"requires":{"env":[]},"optionalEnv":["BINANCE_API_KEY"]}}
dependencies:
  skills:
    - name: derivatives-trading-usds-futures
      source: binance/derivatives-trading-usds-futures
    - name: spot
      source: binance/spot
    - name: trading-signal
      source: binance-web3/trading-signal
    - name: query-token-audit
      source: binance-web3/query-token-audit
    - name: assets
      source: binance/assets
license: MIT
---

# Crayfish Grid Hunter v5.0

## Overview

Crayfish Grid Hunter v5.0 is a **USDS-M Perpetual Futures grid trading assistant** built for the Binance Agent competition. It performs **dual-category market screening** and generates **Geometric Neutral Grid** strategies that comply with the Binance Futures Grid 2026 specification.

**Two screening categories:**

| Category | Chinese Name | Target | Grid Strategy |
| :--- | :--- | :--- | :--- |
| **Category A** | 次新币横盘类 | Listed < 60 days, post-pullback sideways consolidation | Geometric Neutral, 20–30 grids |
| **Category B** | 高波动套利类 | RV > 15%/yr, Volume/OI > 30%, 24h vol 5%–40% | Geometric Neutral, 30–60 grids |

---

## Trigger Conditions

Activate this skill when the user mentions any of the following:
- "次新币横盘" / "高波动套利" / "两个分类" / "双分类筛选"
- "网格交易" / "合约网格" / "期货网格" / "grid trading"
- "Geometric网格" / "等比网格" / "中性网格" / "Neutral Grid"
- "哪个币适合做网格" / "which coin is good for grid trading"
- "网格参数" / "强平价格" / "funding收益"

---

## Workflow

### Step 0: Dual-Category Screening (双分类筛选)

**Goal**: Output exactly 3 candidates per category, each with current price, 24h volatility, support, and resistance.

#### 0.1 Fetch Universe

Call the `derivatives-trading-usds-futures` skill to get all active USDS-M perpetual symbols:

*   **Skill**: `derivatives-trading-usds-futures`
*   **API**: `GET /fapi/v1/exchangeInfo`
*   **Authentication**: Not required
*   **Filter**: `contractType = PERPETUAL`, `quoteAsset = USDT`, `status = TRADING`

#### 0.2 Fetch Market Data

For each candidate symbol, call:

1.  **24hr Ticker** — price, volume, high/low:
    *   **API**: `GET /fapi/v1/ticker/24hr`
    *   **Params**: `symbol=<SYMBOL>`
    *   **Authentication**: Not required

2.  **Mark Price & Funding Rate**:
    *   **API**: `GET /fapi/v1/premiumIndex`
    *   **Params**: `symbol=<SYMBOL>`
    *   **Authentication**: Not required
    *   **Returns**: `markPrice`, `indexPrice`, `lastFundingRate`, `nextFundingTime`

3.  **Open Interest**:
    *   **API**: `GET /fapi/v1/openInterest`
    *   **Params**: `symbol=<SYMBOL>`
    *   **Authentication**: Not required

4.  **Daily Klines** (30 candles for technical analysis):
    *   **API**: `GET /fapi/v1/klines`
    *   **Params**: `symbol=<SYMBOL>&interval=1d&limit=30`
    *   **Authentication**: Not required

#### 0.3 Category A Screening — Recent Listings (次新币横盘类)

Apply all three filters. A symbol qualifies if **at least one** sideways indicator is met:

| Filter | Condition | Data Source |
| :--- | :--- | :--- |
| Listing age | `onboardDate` within 60 days | `exchangeInfo` |
| ATR(14) | `ATR(14) < 2%` of last price | Daily klines |
| Bollinger Band width | `BB_width < 5%` (standard 20-period) | Daily klines |
| ADX(14) | `ADX(14) < 20` (sideways market) | Daily klines |

**Scoring**: Lower ATR + narrower BB + lower ADX + more recent listing = higher score.

#### 0.4 Category B Screening — High Volatility Arbitrage (高波动套利类)

All three conditions must be met:

| Filter | Condition | Data Source |
| :--- | :--- | :--- |
| Realized Volatility | Annualized RV > 15% (from daily log returns) | Daily klines |
| Volume/OI Ratio | `quoteVolume / openInterest > 0.30` | Ticker + OI |
| 24h Intraday Range | `(high - low) / lastPrice` between 5% and 40% | Ticker |

**Scoring**: Higher RV + higher turnover + 24h vol closest to 15%–25% = higher score.

#### 0.5 Output Format (Step 0)

Present results in this exact format:

```
【次新币横盘类 — Recent Listings (Category A)】
  1. XXXUSDT  Current: $xx.xxxx  24h-Vol: xx.xx%  Support: $xx.xxxx  Resistance: $xx.xxxx
     → Listed Xd ago; ATR=X.XX%, BB-width=X.XX%, ADX=X.X
  2. ...
  3. ...

【高波动套利类 — High Volatility Arbitrage (Category B)】
  1. XXXUSDT  Current: $xx.xxxx  24h-Vol: xx.xx%  Support: $xx.xxxx  Resistance: $xx.xxxx
     → RV=XX.X%/yr, Vol/OI=X.XXx, 24h-vol=XX.XX%
  2. ...
  3. ...
```

---

### Step 1: Geometric Neutral Grid Strategy (合约中性网格)

For each screened symbol, generate a complete Geometric Neutral Grid strategy.

#### 1.1 Grid Type and Direction

*   **Grid Type**: **Geometric (等比网格)** — each price level is separated by a constant ratio `r`, not a fixed dollar amount. This is the industry standard for volatile assets as it provides equal percentage profit at every level.
*   **Direction**: **Neutral (中性)** — no initial position bias. The grid places buy orders below current price and sell orders above, profiting from oscillation in both directions.

#### 1.2 Grid Range Calculation

The grid range is anchored to three technical levels, taking the **tightest valid range**:

```
lower = max(BB_lower_20, swing_support_20, current_price - 3×ATR)
upper = min(BB_upper_20, swing_resistance_20, current_price + 3×ATR)
```

*   **BB lower/upper**: Standard 20-period Bollinger Bands (2σ) from daily klines
*   **Swing support/resistance**: Lowest low / highest high of the last 20 daily candles
*   **ATR buffer**: `3 × ATR(14)` from daily klines
*   **Minimum range**: If `(upper - lower) / price < 5%`, expand to `price ± 2.5%`

#### 1.3 Grid Count Selection

| 24h Volatility | Grid Count |
| :--- | :--- |
| ≥ 25% | 50 grids |
| 15% – 25% | 40 grids |
| 8% – 15% | 30 grids |
| < 8% | 20 grids |

#### 1.4 Geometric Ratio and Per-Grid Profit

The geometric ratio `r` is derived from the price range and grid count:

```
r = (upper / lower) ^ (1 / n)
```

Per-grid net profit after fees:

```
profit_per_grid = (r - 1) - 2 × maker_fee
```

Where `maker_fee = 0.04%` (standard rate; 0.02% with BNB burn enabled).

**Minimum profit enforcement**: If `profit_per_grid < 0.8%`, reduce grid count until the minimum is satisfied:

```
min_r = 1 + 0.008 + 2 × 0.0004 = 1.0088
n_adjusted = floor(log(upper/lower) / log(min_r))
```

**Target profit range**: 0.8% – 1.2% per grid after fees.

#### 1.5 Risk Parameters

**5% Hard Stop-Loss**:
```
stop_loss = lower × 0.95
```
If price falls below `stop_loss`, close all grid orders immediately.

**Liquidation Price Estimate** (cross margin, simplified):
```
liquidation_price ≈ lower × (1 - 1/leverage + maintenance_margin_rate)
```
Where `maintenance_margin_rate = 0.4%` (standard for most symbols).

**Maximum account exposure**: Single grid position ≤ 8% of total account balance.

#### 1.6 Funding Rate Analysis

Funding is settled every 8 hours (3× per day). Query the latest rate:

*   **API**: `GET /fapi/v1/premiumIndex` → field `lastFundingRate`
*   **Authentication**: Not required

**Decision logic**:

| Condition | Action |
| :--- | :--- |
| `funding_rate < 0` AND grid is long-biased | Alert: "Long grid earns ~`abs(rate) × 3 × 100`%/day from funding" |
| `funding_rate > 0.001` AND grid is short-biased | Alert: "Short grid earns ~`rate × 3 × 100`%/day from funding" |
| `funding_rate > 0.003` AND grid is long-biased | Warning: "High positive funding rate — long grid pays significant funding costs" |

**Daily funding yield formula**:
```
daily_yield_pct = abs(funding_rate) × 3 × 100
```

#### 1.7 Output Format (Step 1)

Present each symbol's strategy in this exact format:

```
针对 XXXUSDT：
  策略类型    : 合约中性网格（Neutral）
  网格类型    : Geometric 等比
  当前价格    : $xx.xxxx
  网格区间    : $xx.xxxx — $xx.xxxx
  网格数量    : XX grids
  网格比率(r) : X.XXXXXX
  单格利润率  : X.XX%（扣 0.04% 手续费后）
  杠杆倍数    : Xx
  5%硬止损位  : $xx.xxxx（下轨下方5%）
  强平价估算  : $xx.xxxx
  24h波动率   : XX.XX%
  支撑 / 压力 : $xx.xxxx / $xx.xxxx
  Funding提醒 : funding rate -0.012%，多头网格每日预期收益 +0.036%
  网格评分    : XX/100
```

---

### Step 2: Smart Money Signal Validation (聪明钱验证)

Cross-validate screened symbols against Smart Money signals.

*   **Skill**: `trading-signal`
*   **API**: `POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money`
*   **Request Body**:
    ```json
    {
        "page": 1,
        "pageSize": 20,
        "chainId": "CT_501"
    }
    ```
*   **Scoring**: If a screened symbol has an active BUY signal → add +15 to grid score, mark "Smart Money: BUY".

---

### Step 3: Security Audit (安全审计)

For BSC-based tokens (BEP-20), run a security audit before finalizing recommendations.

*   **Skill**: `query-token-audit`
*   **API**: `POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit`
*   **Request Body**:
    ```json
    {
        "binanceChainId": "56",
        "contractAddress": "<contract_address>",
        "requestId": "<uuid-v4>"
    }
    ```
*   **Note**: For major CEX perpetual contracts (BTC, ETH, SOL, etc.) without a BSC contract address, skip this step — no security penalty applied.
*   **Decision**:
    *   **SAFE**: Add +5 to score, display "Security: PASSED"
    *   **WARNING**: Proceed with prominent risk warning
    *   **DANGEROUS**: Auto-exclude from recommendations

---

### Step 4: Fee Optimization (费用优化, Optional)

Requires `BINANCE_API_KEY`.

*   **Skill**: `assets`
*   **API**: `GET /sapi/v1/bnbBurn` — check BNB burn status
*   **API**: `GET /fapi/v2/balance` (via `derivatives-trading-usds-futures`) — check futures account balance
*   **Authentication**: Required (API Key + HMAC-SHA256 signature)
*   **Action**: If `feeBurn` is `false`, recommend enabling it. With BNB burn, maker fee drops from 0.04% to 0.02%, increasing per-grid profit by ~0.04%.

---

### Step 5: Performance Monitoring & Alerting (性能监控)

After a grid is activated, use the `GridPerformanceMonitor` (defined in `monitor.py`) for real-time health tracking across four dimensions:

#### 5.1 Grid Performance

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| PnL ≤ −5% of invested capital | **CRITICAL** | Recommend stopping the grid immediately |
| PnL ≤ −3% of invested capital | **HIGH** | Prompt user to review grid settings |
| Fill rate ≤ 5% (grid stalled) | **HIGH** | Suggest range adjustment or market exit |
| Fill rate ≤ 20% (low activity) | **MEDIUM** | Advisory: market may be trending |
| PnL ≥ +5% milestone reached | **INFO** | Positive status update to user |

#### 5.2 Market Condition

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| Price within 3% of grid boundary | **CRITICAL** | Warn of imminent breakout |
| Price within 8% of grid boundary | **HIGH** | Advisory: monitor closely |
| Price exits grid range entirely | **CRITICAL** | Notify grid is now inactive |
| Volume ≥ 2.5× 24h average | **CRITICAL** | Breakout signal — review position |
| Price drifted >2% from entry | **MEDIUM** | Suggest re-centering the grid |

#### 5.3 Risk Management (Futures-Specific)

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| Price within 2% of stop-loss | **CRITICAL** | Immediate stop-loss warning |
| Price within 5% of stop-loss | **HIGH** | Prepare for potential stop-loss execution |
| Price within 10% of liquidation price | **CRITICAL** | Emergency: reduce leverage or add margin |
| Drawdown from peak ≥ 8% | **CRITICAL** | Recommend emergency exit |
| Funding rate turns positive (>0.1%) | **HIGH** | Long grid now paying funding — review |

#### 5.4 API Health

| Condition | Alert Level | Action |
| :--- | :--- | :--- |
| Average latency ≥ 3000ms | **HIGH** | Warn of degraded data freshness |
| Error rate ≥ 20% | **HIGH** | Warn of unreliable data |
| Fallback endpoint active | **MEDIUM** | Notify primary API is unreachable |

#### 5.5 Funding Rate Monitoring (New in v5.0)

```python
# In the agent monitoring loop:
if funding_rate < 0 and grid_direction == "long":
    alert_funding_profit(expected_daily_yield_pct)

if funding_rate > 0.003 and grid_direction == "long":
    alert(HIGH, f"Funding rate {funding_rate*100:.4f}% is high — long grid paying {funding_rate*3*100:.3f}%/day")

if price < stop_loss_5pct or price < liquidation_price * 1.05:
    close_all_grids()  # Emergency exit
```

---

## Authentication

This skill **does not require** a Binance API key for its core market scanning, screening, and grid calculation functions. All public endpoints (`/fapi/v1/exchangeInfo`, `/fapi/v1/ticker/24hr`, `/fapi/v1/premiumIndex`, `/fapi/v1/klines`, `/fapi/v1/openInterest`) are accessible without authentication.

An API key is required only for account-specific features (balance checks, fee optimization, order placement):

```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_secret_key"
```

---

## User-Agent Header

When making API calls via the `derivatives-trading-usds-futures` skill, include:

```
User-Agent: crayfish-grid-hunter/5.0.0 (derivatives-trading-usds-futures Skill)
```

When making API calls via `trading-signal` or `query-token-audit` skills, include:

```
User-Agent: crayfish-grid-hunter/5.0.0 (binance-web3 Skill)
```

---

## Grid Score Reference

The composite grid score (0–100+) is calculated as follows:

| Component | Max Points | Criteria |
| :--- | :--- | :--- |
| Sideways strength (Cat A) | 40 | ATR < 2%, BB-width < 5%, ADX < 20 |
| Listing recency (Cat A) | 20 | Newer listing = higher score |
| Realized volatility (Cat B) | 40 | Higher RV = higher score (capped at 40) |
| Turnover ratio (Cat B) | 30 | Higher Vol/OI = higher score |
| Optimal 24h vol (Cat B) | 30 | 15%–25% range = max score |
| Smart Money BUY signal | +15 | Active BUY signal from `trading-signal` |
| Security audit SAFE | +5 | SAFE result from `query-token-audit` |
