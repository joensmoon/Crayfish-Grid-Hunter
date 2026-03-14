# API Usage Guide

This document provides detailed instructions on how Grid Hunter uses each of its 5 integrated Binance skills to gather data and execute its workflow.

## 1. Fetching Market Rankings (crypto-market-rank)

To identify potential trading pairs, first get a list of top-traded tokens by volume.

*   **Skill**: `crypto-market-rank`
*   **API**: `Unified Token Rank`
*   **Method**: `POST`
*   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list`
*   **Authentication**: None required (public endpoint)
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

| Parameter | Value | Description |
| :--- | :--- | :--- |
| `rankType` | 10 | Trending tokens |
| `period` | 50 | 24-hour period |
| `sortBy` | 70 | Sort by volume |
| `size` | 200 | Number of tokens to fetch |

## 2. Fetching Historical Price Data (spot)

For each token identified in the market scan, fetch its historical Kline/Candlestick data.

*   **Skill**: `spot`
*   **API**: `/api/v3/klines`
*   **Method**: `GET`
*   **URL**: `https://api.binance.com/api/v3/klines`
*   **Authentication**: None required for market data

**Example (14-day daily data for volatility analysis)**:

```
GET /api/v3/klines?symbol=LINKUSDT&interval=1d&limit=14
```

**Example (72-hour hourly data for range generation)**:

```
GET /api/v3/klines?symbol=LINKUSDT&interval=1h&limit=72
```

**Kline Response Format** (each element is an array):

| Index | Field | Type |
| :--- | :--- | :--- |
| 0 | Open time | Timestamp (ms) |
| 1 | Open price | String |
| 2 | High price | String |
| 3 | Low price | String |
| 4 | Close price | String |
| 5 | Volume | String |
| 6 | Close time | Timestamp (ms) |

## 3. Smart Money Signals (trading-signal)

Query Smart Money buy/sell signals to validate grid trading candidates.

*   **Skill**: `trading-signal`
*   **API**: `Smart Money Signal List`
*   **Method**: `GET`
*   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/signal/smart-money/list`
*   **Authentication**: None required (public endpoint)
*   **Parameters**:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `chainId` | String | `56` for BSC, `CT_501` for Solana |
| `page` | Integer | Page number (default: 1) |
| `size` | Integer | Results per page (default: 50) |

**Response Fields of Interest**:

| Field | Description |
| :--- | :--- |
| `symbol` / `tokenSymbol` | Token symbol |
| `direction` / `side` | Signal direction (BUY/SELL) |
| `triggerPrice` | Price at which the signal was triggered |
| `currentPrice` | Current price of the token |
| `maxGain` / `maxGainRate` | Maximum gain percentage since signal |
| `exitRate` | Exit rate percentage |

**Grid Hunter Integration Logic**:

When a candidate token matches a Smart Money BUY signal, Grid Hunter adds +15 bonus points to its composite score. A SELL signal adds a warning note but does not auto-exclude the candidate, because grid trading profits from price oscillation regardless of overall direction.

## 4. Token Security Audit (query-token-audit)

Perform a security audit on candidate tokens before recommending them.

*   **Skill**: `query-token-audit`
*   **API**: `Token Audit Query`
*   **Method**: `GET`
*   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/token/audit/query`
*   **Authentication**: None required (public endpoint)
*   **Parameters**:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `address` | String | Token contract address |
| `chainId` | String | `56` (BSC), `1` (Ethereum), `CT_501` (Solana) |

**Risk Assessment Matrix**:

| Risk Category | Check Fields | DANGEROUS Threshold |
| :--- | :--- | :--- |
| Honeypot | `isHoneypot`, `honeypot` | `true` |
| Rug Pull | `isRugPull`, `rugPull` | `true` |
| Buy/Sell Tax | `buyTax`, `sellTax` | > 10% |
| Contract Verification | `isOpenSource`, `contractVerified` | `false` (WARNING only) |
| Owner Privileges | `ownerCanMint`, `ownerCanPause` | `true` (WARNING only) |

**Decision Logic**:

The agent classifies tokens into three safety levels based on the audit results. Tokens classified as DANGEROUS are automatically excluded from recommendations. Tokens with WARNING status are still recommended but include a prominent risk notice. Tokens that pass all checks receive a SAFE label and a small score bonus.

## 5. Fee Optimization (assets)

Check and optimize the user's trading fee settings.

*   **Skill**: `assets`
*   **Authentication**: Required (API Key + HMAC-SHA256 signature)

**Check BNB Burn Status**:

```
GET /sapi/v1/bnbBurn
```

This returns `{"spotBNBBurn": true/false, "interestBNBBurn": true/false}`. If `spotBNBBurn` is `false`, Grid Hunter recommends enabling it to save approximately 25% on trading fees.

**Check Account Balance**:

```
POST /sapi/v1/asset/getUserAsset
```

This returns the user's asset balances. Grid Hunter uses this to verify the user has sufficient funds for the recommended grid configuration.

**Query Trading Fee Rate**:

```
GET /sapi/v1/asset/tradeFee?symbol=<SYMBOL>
```

This returns the maker/taker fee rates for a specific trading pair, allowing Grid Hunter to factor fees into its estimated daily return calculation.
