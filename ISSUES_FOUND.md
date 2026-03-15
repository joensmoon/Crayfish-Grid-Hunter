# Deep Test Issues Found — v2.0.0

## Critical Issues

### BUG-1: Category A 筛选逻辑错误 — 量缩比率计算
**问题**: `screen_recent_contracts` 中，量缩比率 `vol_ratio` 使用的是 `volumes[-1] / avg_7d`，
但 `volumes` 来自日线 klines，最后一根 K 线是当天（可能未收盘），且 7 日均量计算窗口不正确。
测试中 FRESHUSDT (62天, ADX=16.8) 和 RECENTUSDT (78天, ADX=18.5) 本应通过筛选但被过滤掉了。
**根因**: `vol_ratio` 计算使用了错误的窗口，导致量缩判断失效。

### BUG-2: 网格区间计算错误 — 上轨高于当前价格
**问题**: 对于 VOLATILUSDT (price=$0.2345)，网格区间为 $0.2078–$0.2318，
上轨 $0.2318 < 当前价格 $0.2345，说明当前价格在网格区间之外！
这意味着策略无法正常运行，网格应该包含当前价格。
**根因**: `calculate_geometric_grid` 中 upper 被 `min(bb_upper, resistance, price+3*ATR)` 限制，
当 resistance < price 时，upper 会低于当前价格。

### BUG-3: 网格数量不匹配波动率
**问题**: HOTCOINUSDT (24h波动=18.5%) 和 VOLATILUSDT (22.3%) 都应该使用 40 格（15-25%区间），
但实际输出为 11 和 12 格。说明最低利润强制执行逻辑将网格数从 40 压缩到了 11/12，
但这是因为网格区间太窄（只有 5% 左右），不是真正的高波动网格。
**根因**: 网格区间计算过窄，导致高波动标的的网格数被强制压缩。

### BUG-4: VERSION 显示错误
**问题**: 输出底部显示 `v1.0.0` 而不是 `v2.0.0`。
**根因**: `grid_hunter_v5.py` 中 `VERSION = "1.0.0"` 未更新。

## Medium Issues

### BUG-5: Category A 摘要表格列名混乱
**问题**: format_scan_output 的 Category A 表格头部显示 `Age` 列，
但实际填充的是 `volatility_24h_pct`（24h波动率），不是合约年龄。
列名与数据不匹配。

### BUG-6: 量缩比率显示 "50%" 而非真实值
**问题**: NEWCOINUSDT 显示 "成交量萎缩至50%"，但我们设置的是 vol_shrink=0.28（28%）。
说明 vol_ratio 计算没有使用我们 patch 的数据，而是用了原始 volumes 计算。

### BUG-7: 参数建议引擎未获取 ADX 数据
**问题**: `format_scan_output` 调用 `advisor.analyze()` 时只传了 `avg_vol`，
未传 `avg_adx`，导致市场状态始终显示"横盘震荡"，即使高波动标的存在。

### BUG-8: 网格详情重复输出
**问题**: `format_scan_output` 末尾已经调用了 `gp.to_display()`，
但 `INDIVIDUAL GRID DETAILS` 部分又重复输出了一遍。
在实际 AI Agent 使用中，这会导致输出过长。

### BUG-9: 负资金费率提示不够突出
**问题**: HOTCOINUSDT 的负资金费率 (-0.05%) 是重要的套利机会，
但提示文字 "多头网格每日预期收益 +0.150%" 淹没在其他信息中，
没有在摘要表格中单独标注。

## Minor Issues

### BUG-10: 强平价估算公式不精确
**问题**: `liq_price = lower * (1 - 1/leverage + maintenance_margin_rate)`
对于 5× 杠杆，liq = lower * (1 - 0.2 + 0.004) = lower * 0.804
HOTCOINUSDT: lower=$3.2832, liq=$2.6397 (实际 3.2832 * 0.804 = 2.6397 ✓)
但这个公式假设仓位在下轨建立，实际中性网格的强平价应基于总仓位，
应该提示这是估算值，实际以交易所显示为准。

### BUG-11: 次新币表格缺少合约年龄列
**问题**: Category A 表格头部有 `Age` 列但填充的是波动率，
应该显示合约上线天数（这是次新币最重要的筛选维度）。

### BUG-12: 回测报告中 grid_utilization 计算会崩溃
**问题**: `format_report` 中调用 `GridBacktester(c).grid_levels`，
每次格式化报告都会重新实例化 GridBacktester，性能浪费且可能出错。
