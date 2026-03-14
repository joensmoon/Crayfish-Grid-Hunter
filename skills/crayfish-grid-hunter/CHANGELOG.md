# Changelog

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
