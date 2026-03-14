# Changelog

## [4.1.0] - 2026-03-15

### Fixed

*   **SKILL.md metadata 格式修复**: 将多行 YAML 格式的 metadata 修复为 OpenClaw 规范要求的单行 JSON 格式。
*   **Spot API Fallback 机制**: 为 `test_grid_hunter.py` 添加了自动 fallback 逻辑，当 `api.binance.com` 返回 451 时自动切换到 `data-api.binance.vision`。
*   **API 定义同步**: 统一了 `SKILL.md`、`api_usage.md` 和测试脚本中关于 `trading-signal` 和 `query-token-audit` 的 API 方法（统一为 POST）和 URL。
*   **README 安装 URL 修复**: 修正了 README.md 中的一键安装命令 URL。
*   **LICENSE 署名修复**: 将版权持有人从 "Grid Hunter Contributors" 修正为 "joensmoon"。
*   **User-Agent 统一**: 统一所有 API 调用的 User-Agent 为 `crayfish-grid-hunter/4.1.0 (Skill)`。

### Added

*   **OpenClaw Gating 配置**: 在 SKILL.md metadata 中添加了 `openclaw.requires.env` 声明，明确要求 `BINANCE_API_KEY`。
*   **真实依赖检查**: 测试脚本现在会检查环境变量配置。
*   **突破预警逻辑验证**: 测试脚本新增了对 Step 7 突破预警逻辑的模拟验证。
*   **Kline 响应格式补充**: 在 `api_usage.md` 中补充了完整的 Kline 响应字段说明（Index 0-11）。

### Improved

*   **测试脚本稳定性**: 优化了 API 调用超时和错误处理，减少了 SSL 握手失败导致的 WARN。
*   **Smart Money 验证逻辑**: 测试脚本现在会根据真实的 Smart Money 信号列表为候选币种加分，而非硬编码。

## [4.0.0] - 2026-03-14

### Added — New Skill Integrations

*   **`trading-signal` integration (Step 3)**: Smart Money signal validation.
*   **`query-token-audit` integration (Step 4)**: Automated security audit.
*   **`assets` integration (Step 5)**: Account balance and BNB burn optimization.
*   **Breakout Alert system (Step 7)**: Continuous monitoring for price/volume spikes.
*   **Composite scoring system**: New 0-115 point scoring.

## [3.1.0] - 2026-03-14

### Fixed

*   Added `dependencies` field in SKILL.md.
*   RSI calculation upgraded to Wilder smoothing method.
*   Author placeholder replaced with `GridHunterDev`.

## [1.0.0] - 2026-03-12

*   Initial release.
