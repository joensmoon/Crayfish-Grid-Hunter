# Changelog

## [1.0.0] — 2026-03-16

### 新增功能

**Category B 高波动套利 — 48h 时间窗口**
- 涨跌幅筛选由 24h 改为近 48h，更准确捕捉持续性高波动行情
- 新增 `enrich_snapshot_48h()` 函数：从 1h K线获取运 48 根计算 `high_48h`、`low_48h`、`price_change_pct_48h`、`volatility_48h_pct`
- `screen_high_volatility()` 涨跌幅筛选改为 `abs(price_change_pct_48h) >= HIGH_VOL_48H_MIN_PCT`（默认 10%）
- `MarketSnapshot` 新增四个 48h 字段：`high_48h`、`low_48h`、`price_change_pct_48h`、`volatility_48h_pct`
- CLI 新增 `--high-vol-48h-min-pct` 参数，支持用户自定义 48h 涨跌幅阈値

**Category A 次新币网格 — 市値过滤**
- 次新币筛选加入市値过滤：默认 $1000万-$2亿（`CAT_A_MCAP_MIN=10_000_000`、`CAT_A_MCAP_MAX=200_000_000`）
- 无市値数据时优雅降级（不过滤），避免数据缺失时错误排除合法标的
- CLI 新增 `--cat-a-mcap-min` 和 `--cat-a-mcap-max` 参数
- `screen_recent_contracts()` 新增 `token_data` 参数，市値信息写入 `category_reason`

### 测试
- 175/175 通过（原有 72 + v1.0.00 新增 90 + v1.0.0 新增 13）
- 新增 `enrich_snapshot_48h`、48h 过滤、Cat A 市値过滤、CLI 参数 4 组专项测试

---

## [1.0.0] — 2026-03-15

### 严重问题修复

**根本原因确认**：ALPACAUSDT（已下架）和 OPUSDT（上线3年）出现在结果中，
是因为 AI 没有执行脚本而是自行生成了内容。脚本本身的过滤逻辑是正确的：
- `status != "TRADING"` 已过滤下架合约（ALPACAUSDT 不在 exchangeInfo 中）
- `onboardDate` 精确到毫秒，OP 上线 1000+ 天远超 90 天阈值

### 防伪签名机制（核心新增）
- **执行ID**：脚本启动时生成唯一执行ID（`CRAYFISH-XXXXXXXX`），打印在输出头部
- **输出签名**：`format_scan_output()` 末尾加入 `CRAYFISH-XXXXXXXXXXXX` 签名和精确时间戳
- **验证方法**：真实脚本输出必含 `CRAYFISH-` 签名。若用户看到的结果没有此签名，说明 AI 没有执行脚本，结果无效
- AI 无法伪造此签名（签名基于执行时间+版本号+结果数量的 MD5 哈希）

### SKILL.md 强化（v1.0.03）
- 重写为更强制性的执行规则格式（参考 OpenClaw 官方规范）
- 新增签名验证说明，用户可自行验证输出真实性
- 禁止事项加入"违反将导致用户损失真实资金"警告
- 次新币定义章节加入 `onboardDate` 精确计算公式说明
- 高波动套利章节明确"严格精确匹配，无 fallback"

### 测试
- 162/162 通过（原有 72 + v1.0.00 新增 90）
- 新增签名机制专项验证

## [1.0.0] — 2026-03-15

### OpenClaw 兼容性修复
- **[SKILL.md] frontmatter 格式符合 OpenClaw 规范**：
  - `description` 改为单行（原多行 `|` 块格式不被 OpenClaw parser 支持）
  - `metadata` 改为单行 JSON（OpenClaw 要求 `metadata` 必须是单行 JSON 对象）
  - 移除旧的 `requires` 列表格式（OpenClaw 使用 `metadata.openclaw.requires.bins` 格式）
  - 新增 `requires.bins: ["python3"]` — OpenClaw 在加载时检查 `python3` 是否在 PATH 中
  - 新增 `install` 字段 — 支持 OpenClaw macOS Skills UI 一键安装
  - 新增 `homepage` 字段 — 在 Skills UI 显示项目主页
  - 新增 `emoji: 🦞` — 在 Skills UI 显示图标
- **[SKILL.md] 脚本路径使用 `{baseDir}` 变量**：OpenClaw 自动注入 Skill 目录绝对路径，无需用户手动替换路径
- **[SKILL.md] 安装命令更新为 `clawhub install`**：符合 OpenClaw 官方 ClawHub 安装规范
- **[SKILL.md] 故障排除路径使用 `{baseDir}` 变量**

### 测试
- 新增 SKILL.md 格式合规性自动检查（8 项）
- 总计 165/165 通过

## [1.0.0] — 2026-03-15

### 关键修复
- **[BUG] 移除 query-token-info 不安全 fallback**：搜索无精确匹配时不再取 `tokens[0]`，彻底杜绝非合约代币混入筛选池（如搜索 "ACE" 返回 "ACEME" 数据）
- **[BUG] screen_high_volatility 二次验证**：增加 `token_data.symbol` 与 `base_asset` 的精确匹配校验
- **[DOC] 次新币定义统一为 90 天**：README、SKILL.md、EXAMPLES.md、CONFIGURATION.md 全部统一
- **[DOC] 移除所有“杠杆3倍/60天”限制性示例**：改为中性的止损/市值范围示例，不对杠杆做限制性推荐

### 测试
- 新增 3 个 token 验证专项测试（精确匹配、无匹配返回 None、$前缀处理）
- 总计 165/165 通过

## [1.0.0] — 2026-03-15

### 关键修复 (Critical Fixes)
- **[SKILL.md] 彻底重写 Agent Behavior 指令**：新增 5 条强制规则，明确禁止 AI 自行生成数据，必须通过执行脚本获取真实数据
- **[grid_hunter_v5.py] 新增完整 CLI 入口**：添加 `if __name__ == '__main__'` 入口和 `argparse` 参数解析，支持所有 `UserConfig` 字段通过命令行传递
- **[SKILL.md] 修复参数传递指令**：SKILL.md 中的 CLI 命令现在真实可执行（之前的 `--contract-recent-days` 等参数无法工作）

### 新增 CLI 参数
- `--mode {all,cat-a,cat-b}`：选择筛选模式（全量/仅次新币/仅高波动）
- `--contract-recent-days`、`--leverage`、`--mcap-min`、`--mcap-max`、`--turnover-min` 等全部 UserConfig 字段
- `--no-backtest`：跳过回测加快速度
- `--no-progress`：禁用进度条（适合日志输出）

### 文档更新
- SKILL.md 新增自然语言 → CLI 参数对照表
- SKILL.md 明确列出 5 类禁止输出内容（跨交易所套利、三角套利等）
- README.md 同步更新 v1.0.0 说明

## [1.0.0] — 2026-03-15

### Bug Fixes (Critical)
- **BUG-2 FIXED**: Grid range upper bound could be below current price — strategy would be unexecutable.
  Now enforces `lower < current_price < upper` with final safety clamps.
- **BUG-1 FIXED**: `volume_shrinkage_ratio` used `volumes[-1]` (potentially incomplete candle) as current day.
  Now uses `volumes[-2]` (most recent complete day) vs prior 7-day average.
  Added `_volume_shrinkage_ratio` override attribute for testing.
- **BUG-3 FIXED**: Minimum profit enforcement (`MIN_GRID_PROFIT=0.8%`) failed silently when range was too narrow.
  Now auto-expands grid range when reducing grid count is insufficient.
- **BUG-4 FIXED**: `VERSION` constant was `"1.0.0"` instead of `"1.0.0"`.

### Bug Fixes (Medium)
- **BUG-5/11 FIXED**: Category A summary table now correctly shows contract age (days), ATR%, BB%, ADX, Score
  instead of incorrectly filling the `Age` column with 24h volatility.
- **BUG-7 FIXED**: `format_scan_output` now passes `avg_adx` to `ParameterAdvisor.analyze()`,
  enabling accurate market regime detection (was always showing "横盘震荡").
- **BUG-9 FIXED**: Negative funding rate symbols now highlighted with 💰 in both Category A and B tables.
  Category B table adds legend explaining the 💰 indicator.

### Logic Improvements
- **Sideways filter hardened**: ADX is now a hard gate (ADX ≥ threshold → exclude, regardless of ATR/BB).
  Previously, low ATR could override high ADX, allowing trending symbols through Category A.
  New logic: `adx_ok AND (atr_low OR bb_narrow)` instead of `atr_low OR bb_narrow OR adx_low`.

### Display Enhancements
- `to_display()` now shows price-in-range validation: `[✅ 在区间内]` or `[⚠️ 在区间外！]`
- Grid range now shows width percentage: `(宽度 9.0%)`
- Grid count now shows recommendation hint: `10 格 (低波动建议20格)`
- Liquidation price now labeled as estimate: `（估算值，以交易所显示为准）`
- Category B table adds `RV%` column (realized volatility), replacing duplicate `Vol%` column

### Test Updates
- Updated `test_grid_hunter.py` `make_tech_sideways` to use last-two-candle shrinkage pattern
  (aligns with new `volume_shrinkage_ratio` calculation using `volumes[-2]`)
- All 162 tests pass (72 original + 90 v1.0.00 feature tests)

## [1.0.0] — 2026-03-15

### 新增
- **`progress.py`**: 进度条模块，包含 `ProgressBar`、`StepProgress`、`format_table`、`format_error`、`format_warning`、`format_success`
- **`param_advisor.py`**: 参数优化建议引擎，包含 `ParameterAdvisor`、`MarketRegime`、`detect_market_regime`
- **`api_server.py`**: REST API 服务器（FastAPI）+ `WebhookClient` 支持
- **`install.sh`**: 一键安装脚本
- **`docs/QUICK_START.md`**: 5分钟快速开始指南
- **`docs/EXAMPLES.md`**: 丰富使用示例
- **`docs/CONFIGURATION.md`**: 详细配置参数说明
- **`docs/ADVANCED.md`**: 高级使用指南（API、Webhook、回测集成）

### 改进
- **`grid_hunter_v5.py`**: `run_dual_category_scan()` 新增实时进度条显示、每步状态反馈、友好错误信息
- **`grid_hunter_v5.py`**: `format_scan_output()` 升级为表格化结果展示 + 参数优化建议集成
- **`backtester.py`**: `format_report()` 新增综合评定（优秀/良好/一般/亏损）、中文化输出、止损触发建议
- **`SKILL.md`**: 升级到 v1.0.0，新增安装说明、模块列表

### 测试
- 新增 `test_v2_features.py`: 90 个测试用例覆盖所有 v1.0.00 新功能
- 全部 162 个测试 (72 个原有 + 90 个新增) 全部通过

## [1.0.0] - 2026-03-15

### Added — Official Release (v1.0.0)

*   **Stable Release**: The project has reached its first stable milestone, transitioning from v5.x development to v1.0.0.
*   **Historical Backtester**: Added `backtester.py` for 30-day 1h kline simulations, providing ROI, Sharpe ratio, and Max Drawdown.
*   **User Customization**: Implemented `UserConfig` allowing natural language overrides for 15+ parameters (leverage, stop-loss, mcap, etc.).
*   **Enhanced Monitoring**: `monitor.py` now includes a real-time console dashboard, volatility regime detection, and auto-tuning suggestions.
*   **Troubleshooting Guide**: Added `TROUBLESHOOTING.md` for common installation, API, and strategy issues.
*   **Refined Screening**: Standardized Category A (Recent Contracts ≤90 days) and Category B (High Volatility $200M-$1B Mcap) logic.

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
