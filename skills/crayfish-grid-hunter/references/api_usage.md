# API Usage Guide

This document provides detailed instructions on how Crayfish Grid Hunter v1.0.0 uses Binance official APIs to gather data and execute its workflow.

## Current Dependencies (v1.0.0)

Crayfish Grid Hunter v1.0.0 relies on **2 official Binance Skills**:

| Skill | Source | Purpose |
| :--- | :--- | :--- |
| `derivatives-trading-usds-futures` | binance/binance-skills-hub | Contract list, klines, funding rate, mark price, open interest |
| `query-token-info` | binance-web3/query-token-info | Token market cap, 24h volume, turnover data |

## API Base URLs

| Service | Primary URL | Fallback URL |
| :--- | :--- | :--- |
| Futures API | `https://fapi.binance.com` | `https://testnet.binancefuture.com` |
| Web3 API | `https://web3.binance.com` | N/A |

---

## 1. Futures Contract Data (derivatives-trading-usds-futures)

### 1.1 Exchange Info — Contract List

*   **API**: `GET /fapi/v1/exchangeInfo`
*   **Purpose**: Fetch all USDS-M perpetual futures contracts
*   **Authentication**: None required
*   **Key Fields**: `symbol`, `baseAsset`, `onboardDate`, `status`, `contractType`, `pricePrecision`, `quantityPrecision`
*   **Filters Used**: `status=TRADING`, `contractType=PERPETUAL`, `quoteAsset=USDT`

### 1.2 24hr Ticker — Price & Volume

*   **API**: `GET /fapi/v1/ticker/24hr`
*   **Purpose**: Fetch 24-hour price change statistics for all symbols
*   **Authentication**: None required
*   **Key Fields**: `symbol`, `lastPrice`, `priceChangePercent`, `volume`, `quoteVolume`

### 1.3 Premium Index — Mark Price & Funding Rate

*   **API**: `GET /fapi/v1/premiumIndex`
*   **Purpose**: Fetch mark price and funding rate for a specific symbol
*   **Authentication**: None required
*   **Parameters**: `symbol=<SYMBOL>`
*   **Key Fields**: `markPrice`, `lastFundingRate`

### 1.4 Klines — Historical Candlestick Data

*   **API**: `GET /fapi/v1/klines`
*   **Purpose**: Fetch historical candlestick data for technical analysis (ATR, Bollinger Bands, ADX)
*   **Authentication**: None required
*   **Parameters**: `symbol=<SYMBOL>`, `interval=1d`, `limit=30`

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

### 1.5 Open Interest

*   **API**: `GET /fapi/v1/openInterest`
*   **Purpose**: Fetch open interest for turnover rate calculation
*   **Authentication**: None required
*   **Parameters**: `symbol=<SYMBOL>`

---

## 2. Token Market Data (query-token-info)

### 2.1 Token Search — Market Cap & Volume

*   **API**: `GET /bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search`
*   **Base URL**: `https://web3.binance.com`
*   **Purpose**: Fetch market cap and 24h trading volume for token screening
*   **Authentication**: None required (public endpoint)
*   **Parameters**: `keyword=<BASE_ASSET>`, `orderBy=volume24h`

**Key Response Fields**:

| Field | Description |
| :--- | :--- |
| `symbol` | Token symbol |
| `marketCap` | Market capitalization (USD) |
| `volume24h` | 24-hour trading volume (USD) |
| `createTime` | Token creation time |

**Important**: The code uses **strict exact symbol matching** to avoid cross-contamination. For example, searching "ACE" might return "ACEME" as the first result, but only an exact match to "ACE" will be used.

---

## 3. Future Plans (Not Yet Implemented in v1.0.0)

The following APIs are planned for future integration but are **not used in the current v1.0.0 release**:

### 3.1 Smart Money Signals (trading-signal)

*   **Skill**: `trading-signal` (binance-web3)
*   **Purpose**: Validate grid trading candidates with Smart Money buy/sell signals
*   **Status**: Planned for future release

### 3.2 Token Security Audit (query-token-audit)

*   **Skill**: `query-token-audit` (binance-web3)
*   **Purpose**: Perform security audits on candidate tokens
*   **Status**: Planned for future release

### 3.3 Fee Optimization (assets)

*   **Skill**: `assets` (binance)
*   **Purpose**: Check BNB burn status and optimize trading fees
*   **Status**: Planned for future release

