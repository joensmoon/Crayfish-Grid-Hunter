---
name: crayfish-grid-hunter
description: "Crayfish Grid Hunter is an AI-powered grid trading assistant for Binance. It scans the market for optimal grid trading candidates, validates them with Smart Money signals and security audits, then generates dynamic grid ranges with risk management parameters. Use this skill when users ask about grid trading opportunities, coin screening, grid range analysis, or 'which coin is good for grid trading'."
metadata: {"version":"4.2.0","author":"joensmoon","openclaw":{"requires":{"env":[]},"optionalEnv":["BINANCE_API_KEY"]}}
dependencies:
  skills:
    - name: spot
      source: binance/spot
      version: ">=1.0.0"
      optional: false
      purpose: "Kline/candlestick data, ticker prices, order book depth"
    - name: crypto-market-rank
      source: binance-web3/crypto-market-rank
      version: ">=1.1"
      optional: false
      purpose: "Market rankings, trending tokens, volume leaders"
    - name: trading-signal
      source: binance-web3/trading-signal
      version: ">=1.0"
      optional: true
      purpose: "Smart Money buy/sell signals for candidate validation"
    - name: query-token-audit
      source: binance-web3/query-token-audit
      version: ">=1.4"
      optional: true
      purpose: "Token security audit — honeypot, rug pull, tax detection"
    - name: assets
      source: binance/assets
      version: ">=1.0.0"
      optional: true
      purpose: "Account balance check, BNB burn fee discount activation"
  system:
    - name: python
      version: ">=3.9"
license: MIT
---

# Crayfish Grid Hunter Skill

Crayfish Grid Hunter is a specialized AI assistant that helps users find the best cryptocurrencies for grid trading on Binance. It combines technical analysis with Smart Money intelligence and security auditing to deliver safe, data-driven grid trading recommendations.

## Prerequisites

Before using this skill, the following official Binance skills **must** be installed. Since the current OpenClaw ecosystem does not support automatic dependency resolution, users need to install them manually.

**Required dependencies** (Crayfish Grid Hunter cannot function without these):

| Dependency Skill | Source | Purpose |
| :--- | :--- | :--- |
| `spot` | `binance/spot` | Kline data, ticker prices, order book |
| `crypto-market-rank` | `binance-web3/crypto-market-rank` | Market rankings, volume leaders |

**Optional dependencies** (enhance Crayfish Grid Hunter with extra capabilities):

| Dependency Skill | Source | Purpose |
| :--- | :--- | :--- |
| `trading-signal` | `binance-web3/trading-signal` | Smart Money signal validation |
| `query-token-audit` | `binance-web3/query-token-audit` | Token security audit before recommendation |
| `assets` | `binance/assets` | Balance check, BNB fee discount (Requires API Key) |

**One-command install (all 5 skills):**

```bash
npx skills add https://github.com/binance/binance-skills-hub \
  --skill spot \
  --skill crypto-market-rank \
  --skill trading-signal \
  --skill query-token-audit \
  --skill assets \
  -a openclaw -y
```

## Workflow

When a user asks "Which coins are good for grid trading?" or "Analyze the grid range for $XXX", the agent should follow these steps in order:

### Step 1: Market Scan (Intelligent Screening)

Scan the market to identify high-volume tokens with grid-friendly characteristics.

1.  **Fetch Market Rankings**: Use the `crypto-market-rank` skill to get top-traded tokens.
    *   **Skill**: `crypto-market-rank`
    *   **API**: `Unified Token Rank`
    *   **Method**: `POST`
    *   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list`
    *   **Request Body**:
        ```json
        {
            "rankType": 10,
            "period": 50,
            "sortBy": 70,
            "orderAsc": false,
            "page": 1,
            "size": 200
        }
        ```

2.  **Filter for Grid Candidates**: For each token, fetch 14-day daily Kline data.
    *   **Skill**: `spot`
    *   **API**: `/api/v3/klines`
    *   **Base URL**: `https://api.binance.com` (primary) or `https://data-api.binance.vision` (fallback)
    *   **Parameters**: `symbol=<symbol>`, `interval=1d`, `limit=14`

3.  **AI Evaluation**: Process the data to identify coins with **high volatility but a stable (sideways) trend**.
    *   **Volatility Check**: Calculate ATR over 14 days. Higher ATR = higher volatility.
    *   **Trend Check**: Calculate price trend slope over 7 and 14 days. Slope close to zero = sideways market.
    *   **RSI Check**: Calculate RSI using the Wilder smoothing method over 14 days. Value oscillating between 30-70 is ideal.
    *   **Screening Criteria**: Volatility > 3%, |Trend Slope| < 2.0%, RSI between 25-75.

### Step 2: Dynamic Range Generation

For each promising candidate, generate a dynamic grid range.

1.  **Fetch Detailed Data**: Get 72-hour hourly Kline data.
    *   **Skill**: `spot`
    *   **API**: `/api/v3/klines`
    *   **Parameters**: `symbol=<symbol>`, `interval=1h`, `limit=72`

2.  **Calculate Bollinger Bands**: Compute 20-period Bollinger Bands to identify the current price range.

3.  **Identify Support/Resistance**: Use recent highs and lows from the 72-hour data.

4.  **Generate Range**: Combine Bollinger Bands and support/resistance levels. The grid range lower bound is `max(Bollinger Lower, 72h Support)` and upper bound is `min(Bollinger Upper, 72h Resistance)`.

5.  **Calculate Grid Density**: Based on volatility — 20 grids for low volatility, up to 50 grids for high volatility.

6.  **Set Stop Loss**: 2% below the lower range boundary.

### Step 3: Smart Money Validation (Optional Enhancement)

If the `trading-signal` skill is installed, validate candidates against Smart Money activity.

1.  **Fetch Smart Money Signals**: For each candidate token, query the trading signal API.
    *   **Skill**: `trading-signal`
    *   **API**: `Smart Money Signal`
    *   **Method**: `POST`
    *   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money`
    *   **Request Headers**: `User-Agent: binance-web3/1.0 (Skill)`
    *   **Request Body**:
        ```json
        {
            "page": 1,
            "pageSize": 100,
            "chainId": "CT_501"
        }
        ```

2.  **Cross-Reference**: Check if any candidate token appears in the Smart Money signal list.
    *   If a **BUY signal** exists for a candidate: Add +15 bonus to the grid score and mark as "Smart Money Backed".
    *   If a **SELL signal** exists: Add a warning note but do not auto-exclude.

### Step 4: Security Audit (Optional Enhancement)

If the `query-token-audit` skill is installed, perform a security audit on each candidate.

1.  **Audit Token Contract**: For each candidate, query the token audit API.
    *   **Skill**: `query-token-audit`
    *   **API**: `Token Security Audit`
    *   **Method**: `POST`
    *   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit`
    *   **Request Headers**: `User-Agent: binance-web3/1.4 (Skill)`
    *   **Request Body**:
        ```json
        {
            "binanceChainId": "56",
            "contractAddress": "<contract_address>",
            "requestId": "<uuid-v4>"
        }
        ```

2.  **Risk Assessment**: Evaluate the audit results:
    *   **Contract Risk**: Is the contract verified? Is it a proxy contract?
    *   **Trading Risk**: Are there abnormal buy/sell taxes (>5%)?
    *   **Scam Risk**: Is it flagged as a honeypot?

3.  **Decision Logic**:
    *   **SAFE**: Proceed with recommendation, display "Security: PASSED".
    *   **WARNING**: Proceed but add a prominent risk warning.
    *   **DANGEROUS**: **Auto-exclude** from recommendations.

### Step 5: Fee Optimization (Optional Enhancement)

If the `assets` skill is installed **AND** the user has provided a `BINANCE_API_KEY`, optimize trading fees.

1.  **Check BNB Burn Status**: Query the BNB burn setting.
    *   **Skill**: `assets`
    *   **API**: `/sapi/v1/bnbBurn`
    *   **Method**: `GET`
    *   **Authentication**: Required (API Key + HMAC-SHA256 signature)

2.  **Recommend Activation**: If `spotBNBBurn` is `false`, recommend the user to enable it.

3.  **Check Account Balance**: Query the user's spot account balance via `assets` skill.

### Step 6: Output Generation

Present the findings to the user in a structured format. The agent's response **MUST** include:

*   **Recommended Coin**: `[Coin Name/USDT]`
*   **Reason**: (e.g., "High volatility with a stable sideways trend. Smart Money BUY signal detected.")
*   **Suggested Range**: `[Lower Price] - [Upper Price]`
*   **Grid Density**: `20-50` grids.
*   **Risk Warning**: Stop-loss point (2% below lower range).
*   **Security Status**: "PASSED" / "WARNING" (if audit skill is available)
*   **Smart Money Signal**: "BUY signal at $X" (if signal skill is available)
*   **Grid Score**: A composite score (0-115).

### Step 7: Breakout Alert (Continuous Monitoring)

After a grid recommendation is active, the agent should monitor for breakout conditions:

1.  **Monitor Price**: Periodically check if the current price approaches the grid range boundaries.
2.  **Volume Spike Detection**: If trading volume increases by more than 200% compared to the 24-hour average while price is near the range edge, trigger an alert.

## Authentication

This skill **does not require** a Binance API key for its core market scanning and analysis functions. However, an API key is required for account-specific features like balance checks and fee optimization.

If you wish to use these features, set the following environment variables:

```bash
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_secret_key"
```

## User-Agent Header

When making API calls, include the `User-Agent` header: `crayfish-grid-hunter/4.2.0 (Skill)`.
