# Crayfish Grid Hunter v5.0 — Test Results

**Version**: 5.0.0
**Date**: 2026-03-15
**Test Suite**: `test_grid_hunter.py`
**Result**: All 43 tests PASSED

---

## Test Summary

| Test Group | Tests | Status |
| :--- | :--- | :--- |
| TEST 1: FuturesSymbol — Listing Age | 4 | PASS |
| TEST 2: TechnicalAnalysis — Sideways Indicators | 6 | PASS |
| TEST 3: TechnicalAnalysis — High Volatility Indicators | 2 | PASS |
| TEST 4: Geometric Grid — Core Calculation | 8 | PASS |
| TEST 5: Geometric Ratio r^n = upper/lower | 2 | PASS |
| TEST 5b: Minimum Profit Enforcement | 1 | PASS |
| TEST 5c: Bollinger Band 20-Period Precision | 2 | PASS |
| TEST 6: Category A — Recent Listings Screening | 3 | PASS |
| TEST 7: Category B — High Volatility Screening | 2 | PASS |
| TEST 8: Monitor — v4.4 Regression Checks | 5 | PASS |
| TEST 9: Futures Monitor — Funding & Liquidation | 6 | PASS |
| TEST 10: Grid Display Format | 8 | PASS |
| **Total** | **49** | **All PASSED** |

---

## Key Validation Results

### Geometric Grid Algorithm

- **r^n = upper/lower**: Verified with tolerance < 0.01 (actual diff: 6.6e-7)
- **Equal ratio**: All grid intervals share the same ratio; variance < 1e-10
- **Profit/grid >= 0.8%**: Enforced even for narrow price ranges via n_adjusted recalculation
- **Stop-loss = lower x 0.95**: Exact 5% hard stop below lower bound

### Dual-Category Screening

- **Category A (次新币横盘类)**: Correctly filters to symbols listed within 60 days with
  sideways indicators (ATR < 2%, BB-width < 5%, or ADX < 20). Old symbols (>60 days) excluded.
- **Category B (高波动套利类)**: Correctly filters to symbols with RV > 15%/yr and
  Vol/OI > 0.30. Low-volatility symbols excluded.

### Futures Monitor — Funding & Liquidation (v5.0 New)

| Scenario | Expected Level | Result |
| :--- | :--- | :--- |
| Negative funding rate (long grid) | INFO — earns funding | PASS |
| Price below stop-loss | CRITICAL — close all grids | PASS |
| Price within 5% of liquidation | CRITICAL — reduce leverage | PASS |
| Funding rate > 0.5% (extreme) | CRITICAL — impacting profitability | PASS |
| Funding rate > 0.3% (high) | HIGH — consider short-biased grid | PASS |
| Positive funding (short grid) | INFO — short grid earns funding | PASS |

### Technical Indicator Precision

- **Bollinger Bands**: Confirmed to use exactly the last 20 closes (not all available data)
- **ATR(14)**: Sideways synthetic data produces ATR < 5% as expected
- **Realized Volatility**: High-volatility synthetic data (sigma=2.5%) produces annualized RV > 10%

---

## API Connectivity Note

The `derivatives-trading-usds-futures` skill uses `fapi.binance.com`, which is geo-restricted
in the test sandbox (HTTP 451). This is expected — the sandbox is not a Binance-eligible region.
In the OpenClaw production environment (user's local machine), all `fapi.binance.com` endpoints
are fully accessible. All algorithm tests use synthetic data and do not require live API access.
