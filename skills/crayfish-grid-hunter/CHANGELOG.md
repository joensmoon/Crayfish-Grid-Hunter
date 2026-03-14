# Changelog

## [5.2.0] - 2026-03-15

### Changed — Dual-Category Logic & Pure Official Skills

*   **Category A (次新币横盘类) Definition Updated**:
    *   Now correctly defined as "Contracts listed within 90 days" (`onboardDate <= 90 days`), matching user intent.
    *   Added Volume Shrinkage check: 24h volume must be < 50% of the 7-day average.
    *   Sideways confirmation requires ATR < 2% or BB-width < 5% or ADX < 20.
*   **Category B (高波动套利类) Definition Updated**:
    *   **Pure Official Skill**: Now uses Binance's official `query-token-info` skill to fetch Market Cap, eliminating the need for third-party APIs (like CoinAnk).
    *   Market Cap constraint: Strictly between $200M and $1B.
    *   True Turnover Rate: `quoteVolume / marketCap > 50%`.
*   **Trigger Words Simplified**: "次新币网格", "高波动套利", "网格猎手".

### Changed — Geometric Grid Enforcement

*   **Minimum Profit Guarantee**: Algorithm now automatically recalculates and reduces grid count if `profit_per_grid` falls below 0.8% (after 0.04% maker fee deduction).
*   **Negative Funding Alpha**: Long grids on negative funding rate pairs now output expected daily yield.

## [5.0.0] - 2026-03-15

### Breaking Changes

*   **Futures Market Focus**: The skill now targets USDS-M Perpetual Futures exclusively.
    The previous Spot market workflow (Steps 1–7 using `crypto-market-rank` and `spot` skills)
    has been replaced by the new Futures dual-category workflow using `derivatives-trading-usds-futures`.
*   **New Core Engine**: `grid_hunter_v5.py` replaces the inline code in the old test script.
    It provides `FuturesSymbol`, `MarketSnapshot`, `TechnicalAnalysis`, `GridParameters`,
    `calculate_geometric_grid`, `screen_recent_listings`, and `screen_high_volatility`.

### Added — Dual-Category Screening (双分类筛选)

*   **Category A (次新币横盘类)**: Screens for symbols listed within 60 days that have entered
    sideways consolidation. Filters: `ATR(14) < 2%`, `BB-width < 5%`, `ADX(14) < 20`.
    Scored by recency, ATR tightness, and BB narrowness.
*   **Category B (高波动套利类)**: Screens for high-volatility arbitrage candidates.
    Filters: annualized `RV > 15%`, `quoteVolume/openInterest > 0.30`, 24h intraday range 5%–40%.
    Scored by RV, turnover ratio, and optimal 24h volatility proximity.
*   Both categories output exactly 3 ranked candidates with current price, 24h volatility,
    support, and resistance levels.

### Added — Geometric Neutral Grid (等比中性网格)

*   **Geometric Grid Algorithm**: Implements `r = (upper/lower)^(1/n)` to ensure equal
    percentage profit at every price level. This is the industry standard for volatile assets.
*   **Minimum Profit Enforcement**: If `profit_per_grid < 0.8%`, the grid count is automatically
    reduced until the minimum is satisfied. Target range: 0.8%–1.2% per grid after fees.
*   **Grid Range Calculation**: Anchored to the tightest of: 20-period Bollinger Bands,
    20-day swing support/resistance, and `current_price ± 3×ATR(14)`.
*   **Grid Count by Volatility**: 20 grids (<8% vol), 30 grids (8–15%), 40 grids (15–25%),
    50 grids (≥25%).

### Added — Futures Risk Management

*   **5% Hard Stop-Loss**: `stop_loss = lower × 0.95`. Enforced as a hard rule for all grids.
*   **Liquidation Price Estimate**: `liq = lower × (1 - 1/leverage + maintenance_margin_rate)`.
    Uses `maintenance_margin_rate = 0.4%` (standard for most symbols).
*   **Funding Rate Analysis**: Queries `/fapi/v1/premiumIndex` for the latest funding rate.
    Calculates daily yield (`abs(rate) × 3 × 100`%) and generates alerts for extreme rates.

### Added — Futures Monitor Enhancements (v5.0)

*   **`check_funding_and_liquidation()` function**: A new standalone helper in `monitor.py`
    that implements the Step 5.5 monitoring logic from SKILL.md:
    *   Negative funding → INFO alert (long grid earns funding)
    *   Price ≤ stop-loss → CRITICAL (close all grids)
    *   Price within 5% of liquidation → CRITICAL (reduce leverage)
    *   Funding rate > 0.5% → CRITICAL (extreme cost for long grid)
    *   Funding rate > 0.3% → HIGH (high cost for long grid)
    *   Positive funding for short grid → INFO (short grid earns funding)
*   **New `MonitorThresholds` fields**: `liquidation_proximity_pct` (10%),
    `funding_rate_high_pct` (0.003), `funding_rate_extreme_pct` (0.005).

### Updated

*   `SKILL.md`: Completely rewritten for v5.0. New 5-step workflow (Step 0–5) covering
    dual-category screening, Geometric grid generation, Smart Money validation, security audit,
    fee optimization, and performance monitoring. Added Grid Score reference table.
*   `monitor.py`: Added `check_funding_and_liquidation()` function and three new
    futures-specific threshold fields to `MonitorThresholds`.
*   `test_grid_hunter.py`: Completely rewritten. 43 tests across 10 test groups covering
    all v5.0 algorithms. All tests use synthetic data for offline execution.
*   `TEST_RESULTS.md`: Updated to v5.0 with full test execution report.
*   `README.md`: Updated to v5.0 with new workflow diagram, project structure, and
    install instructions.


## [4.4.0] - 2026-03-15

### Added — Performance Monitoring & Alerting

*   **`monitor.py` — Performance Monitor & Alert Engine**: A new standalone module providing real-time, multi-dimensional health tracking for active grid positions. The monitor runs four independent check groups on every cycle:
    *   **Grid Performance**: Tracks PnL (CRITICAL at −5%, HIGH at −3%) and fill rate (HIGH when ≤5%, MEDIUM when ≤20%). Fires an INFO milestone alert when PnL reaches +5%.
    *   **Market Condition**: Detects price proximity to grid boundaries (CRITICAL within 3%, HIGH within 8%), price-out-of-range events, volume spikes (≥2.5× 24h average), and trend drift (>2% from entry price).
    *   **Risk Management**: Enforces stop-loss discipline (CRITICAL within 2%, HIGH within 5%) and tracks drawdown from the price peak (CRITICAL at ≥8%, HIGH at ≥5%).
    *   **API Health**: Monitors latency (HIGH ≥3000ms, MEDIUM ≥1000ms), error rates (HIGH ≥20%, MEDIUM ≥5%), and fallback endpoint activation across all Binance Skill API calls.

*   **Alert Cooldown System**: Each unique alert condition has a configurable 15-minute cooldown window to prevent alert fatigue.

*   **`create_monitor()` Factory**: A convenience factory function for creating pre-configured monitor instances with commonly adjusted thresholds.

*   **`format_report()` Method**: Generates a human-readable, structured status report covering all active positions, API health metrics, and recent alert history.

### Updated

*   `SKILL.md`: Added Step 8 (Performance Monitoring & Alerting) with four detailed sub-sections (8.1–8.4) covering all alert conditions, thresholds, and an integration code example (8.5). Added alert cooldown documentation (8.6).
*   `README.md`: Updated version to v4.4.0. Added Step 8 to the workflow diagram. Added `monitor.py` to the project structure tree. Updated the workflow step count from 7 to 8.

## [4.3.0] - 2026-03-15

### Fixed — Core Algorithm Correctness

*   **RSI Calculation (Critical Fix)**: The Step 1 Kline fetch `limit` has been increased from `14` to `30`. The Wilder Smoothing RSI algorithm requires more data points than the period length (`n=14`) to produce a meaningful result. With only 14 candles, the calculation always fell back to the neutral value of 50.0, rendering RSI-based screening non-functional. With 30 daily candles (29 deltas), the algorithm now performs 14 warm-up iterations and 15 rolling updates, producing accurate RSI values that reflect real market momentum.

*   **Bollinger Bands (Critical Fix)**: The Bollinger Band calculation has been corrected to use only the most recent **20 closing prices** (standard 20-period SMA), instead of all 72 hourly candles. The previous implementation averaged all available data, producing an artificially wide band that reflected historical extremes rather than current price behavior. This fix ensures the generated grid range is tightly aligned with recent market conditions.

*   **Range Quality Score**: The composite scoring system now correctly implements the Range Quality factor (+10 points when grid range percentage ≥ 5%), which was described in `technical_indicators.md` but missing from the calculation logic.

*   **Breakout Alert Logic**: The breakout alert test now validates real trigger logic with defined alert levels (`CRITICAL`, `HIGH`, `WARNING`) instead of relying on mock pass-through assertions.

### Removed

*   **`audit_notes.md`**: Removed internal development notes from the public repository.

### Updated

*   `SKILL.md`: Updated Step 1 to specify `limit=30` with a clear explanation of why 30 candles are required for RSI. Updated Step 2 to explicitly document the 20-period Bollinger Band window. Added alert level definitions to Step 7.
*   `test_grid_hunter.py`: Added dedicated test cases for RSI data-guard validation (`[TEST 5b]`) and Bollinger Band 20-period correctness (`[TEST 5c]`). Removed all hard-coded score bonuses from the pipeline test.
*   `TEST_RESULTS.md`: Regenerated with v4.3.0 results.

## [4.2.0] - 2026-03-15

### Improved — Feature Tiering & Accessibility

*   **移除强制 API 密钥要求**: 在 `SKILL.md` 的 metadata 中移除了对 `BINANCE_API_KEY` 的强制要求（gating），将其设为可选。
*   **功能分级设计**: 明确区分了核心功能（基于公共 API）和增强功能（基于私有 API）。
    *   **核心功能**: 市场扫描、技术分析、聪明钱验证、安全审计。这些功能现在无需 API 密钥即可使用。
    *   **增强功能**: 账户余额检查、BNB 燃烧费用优化。这些功能仅在用户提供 API 密钥时激活。
*   **优雅降级逻辑**: 优化了测试脚本和工作流说明，确保在缺失 API 密钥时，系统能自动跳过私有功能并继续执行核心分析任务。
*   **文档更新**: 更新了 `SKILL.md` 和 `README.md`，指导用户如何根据需求选择性配置 API 密钥。

### Fixed

*   修复了 `SKILL.md` 中 `optionalEnv` 的声明方式，符合 OpenClaw 最佳实践。
*   统一了测试脚本中的日志输出，将 API 密钥缺失标记为 `INFO` 而非 `WARN`。

## [4.1.0] - 2026-03-15

### Fixed

*   **SKILL.md metadata 格式修复**: 修复为单行 JSON 格式。
*   **Spot API Fallback 机制**: 添加了自动切换到 `data-api.binance.vision` 的逻辑。
*   **API 定义同步**: 统一了所有 API 方法为 POST。
*   **LICENSE 署名修复**: 修正版权持有人为 `joensmoon`。

## [4.0.0] - 2026-03-14

*   Initial release of v4 series with multi-skill integration.
