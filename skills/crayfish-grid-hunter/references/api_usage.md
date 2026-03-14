# API Usage Guide

This document provides detailed instructions on how Crayfish Grid Hunter uses each of its 5 integrated Binance skills to gather data and execute its workflow.

## API Base URLs

The Spot API (`api.binance.com`) may return HTTP 451 in certain regions. In such cases, use the fallback endpoint.

| Environment | Primary URL | Fallback URL |
|---|---|---|
| Spot Mainnet | `https://api.binance.com` | `https://data-api.binance.vision` |
| Web3 API | `https://web3.binance.com` | N/A |

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
*   **URL**: `https://api.binance.com/api/v3/klines` (or `https://data-api.binance.vision/api/v3/klines` as fallback)
*   **Authentication**: None required for market data

**Example (14-day daily data for volatility analysis)**:
`GET /api/v3/klines?symbol=LINKUSDT&interval=1d&limit=14`

**Example (72-hour hourly data for range generation)**:
`GET /api/v3/klines?symbol=LINKUSDT&interval=1h&limit=72`

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
| 7 | Quote asset volume | String |
| 8 | Number of trades | Integer |
| 9 | Taker buy base asset volume | String |
| 10 | Taker buy quote asset volume | String |
| 11 | Ignore | String |

## 3. Smart Money Signals (trading-signal)

Query Smart Money buy/sell signals to validate grid trading candidates.

*   **Skill**: `trading-signal`
*   **API**: `Smart Money Signal`
*   **Method**: `POST`
*   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money`
*   **Authentication**: None required (public endpoint)
*   **Request Body**:
    ```json
    {
        "page": 1,
        "pageSize": 100,
        "chainId": "CT_501"
    }
    ```

**Response Fields of Interest**:

| Field | Description |
| :--- | :--- |
| `symbol` | Token symbol |
| `side` | Signal direction (BUY/SELL) |
| `triggerPrice` | Price at which the signal was triggered |
| `currentPrice` | Current price of the token |
| `maxGainRate` | Maximum gain percentage since signal |
| `exitRate` | Exit rate percentage |

## 4. Token Security Audit (query-token-audit)

Perform a security audit on candidate tokens before recommending them.

*   **Skill**: `query-token-audit`
*   **API**: `Token Security Audit`
*   **Method**: `POST`
*   **URL**: `https://web3.binance.com/bapi/defi/v1/public/wallet-direct/security/token/audit`
*   **Authentication**: None required (public endpoint)
*   **Request Body**:
    ```json
    {
        "binanceChainId": "56",
        "contractAddress": "<contract_address>",
        "requestId": "<uuid-v4>"
    }
    ```

**Risk Assessment Matrix**:

| Risk Category | Check Fields | DANGEROUS Threshold |
| :--- | :--- | :--- |
| Honeypot | `isHoneypot` | `true` |
| Rug Pull | `isRugPull` | `true` |
| Buy/Sell Tax | `buyTax`, `sellTax` | > 10% |
| Contract Verification | `isOpenSource` | `false` (WARNING only) |

## 5. Fee Optimization (assets)

Check and optimize the user's trading fee settings.

*   **Skill**: `assets`
*   **Authentication**: Required (API Key + HMAC-SHA256 signature)

**Check BNB Burn Status**:
`GET /sapi/v1/bnbBurn`

This returns `{"spotBNBBurn": true/false, "interestBNBBurn": true/false}`. If `spotBNBBurn` is `false`, Crayfish Grid Hunter recommends enabling it to save approximately 25% on trading fees.

**Check Account Balance**:
`POST /sapi/v1/asset/getUserAsset`

This returns the user's asset balances. Crayfish Grid Hunter uses this to verify the user has sufficient funds for the recommended grid configuration.
