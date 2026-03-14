# Changelog

## [4.0.0] - 2026-03-14

### Added — New Skill Integrations

*   **`trading-signal` integration (Step 3)**: Smart Money signal validation for grid trading candidates. When a BUY signal is detected for a candidate token, it receives a +15 bonus to its composite score. SELL signals add a warning note without auto-excluding.
*   **`query-token-audit` integration (Step 4)**: Automated security audit before recommendation. Checks for honeypot, rug pull, abnormal buy/sell tax, unverified contracts, and excessive owner privileges. DANGEROUS tokens are auto-excluded.
*   **`assets` integration (Step 5)**: Account balance verification and BNB burn fee discount optimization. Checks if `spotBNBBurn` is enabled and recommends activation for ~25% fee savings.
*   **Breakout Alert system (Step 7)**: Continuous monitoring for price approaching grid range boundaries with volume spike detection (>200% of 24h average).
*   **Composite scoring system**: New 0-115 point scoring combining volatility, RSI, trend, range quality, Smart Money, and security factors.
*   **9 comprehensive test cases**: Covering all 5 integrated skills with both live API calls and mock data validation.

### Changed

*   Version bumped from 3.1.0 to 4.0.0
*   SKILL.md workflow expanded from 3 steps to 7 steps
*   Dependencies expanded from 2 skills to 5 skills (3 optional)
*   User-Agent header updated to `grid-hunter/4.0.0 (Skill)`
*   `api_usage.md` rewritten with documentation for all 5 skills
*   `technical_indicators.md` expanded with composite scoring and breakout alert thresholds
*   README.md rewritten with full workflow diagram and one-command install

### Improved

*   Grid analysis pipeline now accepts optional Smart Money signals and audit results
*   Output format enhanced with Smart Money signal details and security audit status
*   Test suite restructured with result tracking and summary report

## [3.1.0] - 2026-03-14

### Fixed

*   Added `dependencies` field in SKILL.md frontmatter for `spot` and `crypto-market-rank`
*   RSI calculation upgraded from simple average to Wilder smoothing method
*   Author placeholder replaced with `GridHunterDev`
*   Fixed formatting errors in `technical_indicators.md`

### Added

*   Prerequisites section in SKILL.md with explicit install commands
*   Dependency check test (Test 0) and RSI validation test (Test 3.5)
*   Step-by-step installation guide in README.md

## [3.0.0] - 2026-03-13

### Added

*   Full OpenClaw and Binance Skills Hub compatibility
*   SKILL.md with YAML frontmatter following official format
*   Integration with `binance/spot` and `binance-web3/crypto-market-rank`
*   Technical indicators: ATR, RSI, Bollinger Bands, Trend Slope
*   Dynamic grid range generation
*   Concurrent pair scanning and intelligent caching

## [2.0.0] - 2026-03-12

### Added

*   API Key management, concurrent API calls, cache mechanism

## [1.0.0] - 2026-03-12

### Added

*   Initial release with basic grid trading analysis
