# Changelog

## [1.0.0] — 2026-03-16

### Official Release — Crayfish Grid Hunter v1.0.0

**Crayfish Grid Hunter** is a professional-grade intelligent grid trading strategy plugin for Binance USDS-M Perpetual Futures. This is the official v1.0.0 release, featuring dual-category screening, geometric neutral grids, and comprehensive risk management.

### Core Features

**Dual-Category Screening Engine**
- **Category A (次新币横盘类)**: Screens for contracts listed within 90 days that have entered sideways consolidation. Filters: market cap $10M-$200M, volume shrinkage < 50%, ATR < 2%, BB width < 5%, ADX < 20.
- **Category B (高波动套利类)**: Screens for high-volatility arbitrage opportunities. Filters: market cap $200M-$1B, 48h price change > 10%, turnover rate > 50%, realized volatility > 15%.

**Geometric Neutral Grid Algorithm**
- Implements `r = (upper/lower)^(1/n)` to ensure equal percentage profit at every price level.
- Minimum profit enforcement: 0.8%-1.2% per grid after fees.
- Automatic grid range calculation based on Bollinger Bands, support/resistance, and ATR.
- Grid count optimization: 20-50 grids based on volatility regime.

**Anti-Forgery Signature Mechanism**
- Every script execution generates a unique `CRAYFISH-XXXXXXXXXXXX` signature.
- Signature is appended to output with precise timestamp.
- Prevents AI hallucination by making it impossible to forge execution results.
- Users can verify authenticity by checking for the signature in the output.

**Full Parameter Customization**
- 15+ user-customizable parameters via natural language.
- Support for Category A/B thresholds, grid parameters, leverage, stop-loss, etc.
- CLI argument parser with full `argparse` support.
- Automatic parameter validation with user-friendly warnings.

**Comprehensive Risk Management**
- 5% hard stop-loss enforcement below grid lower bound.
- Liquidation price estimation with maintenance margin calculation.
- Funding rate analysis with daily yield calculation.
- Negative funding rate bonus tracking for long-biased grids.

**Historical Backtesting**
- 30-day 1h kline simulations with ROI, Sharpe ratio, and Max Drawdown calculation.
- Comprehensive backtest report with strategy evaluation.
- Optional backtest execution (can be skipped for speed).

**Real-Time Performance Monitoring**
- Grid performance tracking: PnL, fill rate, grid efficiency.
- Market condition monitoring: volatility regime, trend drift detection.
- API health tracking: latency, error rate, fallback activation.
- Risk management alerts: drawdown, stop-loss proximity, exposure monitoring.
- Multi-level alert system: CRITICAL, HIGH, MEDIUM, INFO.

**OpenClaw Native Support**
- Perfect compatibility with OpenClaw Skill specification.
- Automatic `{baseDir}` injection for skill directory paths.
- One-click installation via `clawhub install joensmoon/crayfish-grid-hunter`.
- Seamless integration with official Binance Skills.

### API & Data Sources

All data comes from official Binance APIs:
- **fapi.binance.com**: USDS-M Perpetual Futures contract data, klines, mark prices, funding rates.
- **web3.binance.com**: Market cap data via `query-token-info` skill.

No third-party APIs or manual data entry required.

### CLI Usage

```bash
# Full dual-category scan with defaults
python3 grid_hunter_v5.py

# Category A only: recent contracts ≤90 days
python3 grid_hunter_v5.py --mode cat-a

# Category B only: high volatility arbitrage
python3 grid_hunter_v5.py --mode cat-b

# Custom parameters
python3 grid_hunter_v5.py --leverage 3 --stop-loss-pct 8.0 --top-n 5

# Skip backtest for speed
python3 grid_hunter_v5.py --no-backtest
```

### Trigger Words (OpenClaw)

- `次新币网格` — Category A screening
- `高波动套利` — Category B screening
- `网格猎手` — Full dual-category scan

### Natural Language Customization

```
"次新币网格，杠杆 3 倍，市值上限 1 亿"
"高波动套利，筛选前 5 名，止损设为 3%"
"网格猎手，次新币上线天数改为 60 天，高波动涨跌幅要 15% 以上"
```

### Testing

- **72 core unit tests** covering all algorithms and data structures.
- **100% test pass rate** — all functionality validated.
- Tests cover: contract age classification, technical indicators, geometric grid calculation, screening logic, funding rate analysis, and output formatting.

### Documentation

- **USER_GUIDE.md** — Complete user manual from installation to result interpretation.
- **QUICK_START.md** — 5-minute quick start guide.
- **EXAMPLES.md** — Rich examples of natural language triggers and parameter customization.
- **CONFIGURATION.md** — Detailed parameter configuration reference.
- **ADVANCED.md** — Advanced usage guide for API integration, Webhooks, and backtesting.
- **TROUBLESHOOTING.md** — Common issues and troubleshooting steps.

### Security & Risk Management

- **Data Authenticity**: All data comes from official Binance APIs in real-time.
- **Anti-Forgery**: Unique signature on every output prevents AI hallucination.
- **Risk Control**: Default 5% stop-loss and liquidation price warnings.
- **Investment Disclaimer**: Grid trading carries risk in one-sided markets. Users should set leverage according to their risk tolerance.

### Author

**joensmoon** — Solo developer and maintainer.

### License

MIT License. For learning and research purposes only. Not investment advice.

---

## Version History

This is the official v1.0.0 release. All previous development versions (v5.x, v2.x) have been consolidated into this stable release.
