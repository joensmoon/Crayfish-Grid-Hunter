# Test Results — Crayfish Grid Hunter v1.0.0

**Date**: 2026-03-15  
**Version**: v1.0.0  
**Total Tests**: 162  
**Passed**: 162  
**Failed**: 0  
**Coverage**: Core screening logic, grid calculation, output formatting, v1.0.00 new features

---

## Test Suite 1: Original Tests (72 tests)

| Module | Tests | Passed | Failed |
|:---|:---:|:---:|:---:|
| FuturesSymbol — Contract Age | 6 | 6 | 0 |
| TechnicalAnalysis — Sideways Indicators | 8 | 8 | 0 |
| Bollinger Band Precision | 5 | 5 | 0 |
| ADX Computation | 4 | 4 | 0 |
| GridParameters — Geometric Calculation | 10 | 10 | 0 |
| Category A — 次新币横盘类 | 8 | 8 | 0 |
| Category B — 高波动套利类 | 9 | 9 | 0 |
| UserConfig — Custom Parameters | 6 | 6 | 0 |
| Edge Cases | 5 | 5 | 0 |
| Backtester | 6 | 6 | 0 |
| GridParameters Display | 6 | 6 | 0 |
| Output Formatting | 4 | 4 | 0 |
| **Total** | **72** | **72** | **0** |

## Test Suite 2: v1.0.00 Feature Tests (90 tests)

| Module | Tests | Passed | Failed |
|:---|:---:|:---:|:---:|
| ProgressBar — Basic Operations | 8 | 8 | 0 |
| StepProgress — Multi-step Tracking | 6 | 6 | 0 |
| format_table — ASCII Table Formatting | 8 | 8 | 0 |
| format_error — Error Message Formatting | 6 | 6 | 0 |
| ParameterAdvisor — Market Regime Detection | 8 | 8 | 0 |
| ParameterAdvisor — Suggestions Generation | 10 | 10 | 0 |
| ParameterAdvisor — Report Formatting | 6 | 6 | 0 |
| APIServer — Endpoint Registration | 8 | 8 | 0 |
| WebhookClient — Notification Formatting | 6 | 6 | 0 |
| Backtester — Enhanced Report | 10 | 10 | 0 |
| Backtester — Run Backtest | 8 | 8 | 0 |
| Integration — format_scan_output + advisor | 6 | 6 | 0 |
| **Total** | **90** | **90** | **0** |

---

## v1.0.0 Bug Fixes Verified

| Bug ID | Description | Status |
|:---|:---|:---:|
| BUG-1 | volume_shrinkage_ratio used incomplete candle | ✅ Fixed |
| BUG-2 | Grid upper bound could be below current price | ✅ Fixed |
| BUG-3 | Min profit enforcement failed for narrow ranges | ✅ Fixed |
| BUG-4 | VERSION showed "1.0.0" instead of "1.0.0" | ✅ Fixed |
| BUG-5/11 | Category A table Age column showed wrong data | ✅ Fixed |
| BUG-7 | param_advisor not receiving avg_adx | ✅ Fixed |
| BUG-9 | Negative funding rate not highlighted | ✅ Fixed |
| LOGIC-1 | ADX not a hard gate in sideways filter | ✅ Fixed |

---

## Deep Output Test Results

### Category A — 次新币横盘类

| Symbol | Age | ATR% | BB% | ADX | Score | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| NEWCOINUSDT | 45d | 1.10% | 3.20% | 12.5 | 42/100 | ✅ Pass |
| FRESHUSDT | 62d | 1.50% | 4.10% | 16.8 | 23/100 | ✅ Pass |
| RECENTUSDT | 78d | 1.80% | 4.80% | 18.5 | 10/100 | ✅ Pass |
| OLDCOINUSDT | 150d | — | — | 25.0 | — | ✅ Filtered (age>90d) |
| TRENDINGUSDT | 30d | 1.30% | 3.80% | 32.0 | — | ✅ Filtered (ADX≥20) |

### Category B — 高波动套利类

| Symbol | Mcap | Turnover | RV% | Vol24h | Score | Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| VOLATILUSDT | $320M | 91% | 108% | 22.3% | 86/100 | ✅ Pass |
| HOTCOINUSDT | $450M | 84% | 92% | 18.5% | 86/100 | ✅ Pass 💰 |
| ARBITUSDT | $680M | 31% | — | — | — | ✅ Filtered (turnover<50%) |
| BIGCAPUSDT | $2500M | 20% | — | — | — | ✅ Filtered (mcap>$1B) |
| SMALLCAPUSDT | $80M | 19% | — | — | — | ✅ Filtered (mcap<$200M) |

### Geometric Grid Precision

All 5 grid calculations verified:
- Grid ratio error < 1e-5 ✅
- All prices in range (lower < price < upper) ✅  
- All profit_per_grid ≥ 0.8% (MIN_GRID_PROFIT) ✅
- All stop_loss < lower ✅
