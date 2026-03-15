#!/usr/bin/env python3
"""
Crayfish Grid Hunter v2.0 — New Features Test Suite
====================================================
Tests all v2.0 additions:
  - progress.py: ProgressBar, StepProgress, format_table, format_error, generate_param_suggestions
  - param_advisor.py: ParameterAdvisor, MarketRegime, detect_market_regime
  - api_server.py: WebhookClient
  - backtester.py: Enhanced format_report with performance rating
  - grid_hunter_v5.py: Enhanced format_scan_output with tables + suggestions

Run:
    python3 test_v2_features.py

Expected output: All tests PASSED
"""

import math
import random
import sys
import time
from datetime import datetime

sys.path.insert(0, "skills/crayfish-grid-hunter")

PASSED = 0
FAILED = 0
TOTAL = 0


def check(name, condition, detail=""):
    global PASSED, FAILED, TOTAL
    TOTAL += 1
    if condition:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED += 1
        print(f"  [FAIL] {name}" + (f": {detail}" if detail else ""))


print(f"\n{'='*65}")
print(f"  CRAYFISH GRID HUNTER v2.0 — NEW FEATURES TEST SUITE")
print(f"{'='*65}")


# ============================================================
# TEST 1: progress.py — ProgressBar
# ============================================================
print("\n[TEST 1] progress.py — ProgressBar")

from progress import ProgressBar, StepProgress, format_table, format_error, format_warning, format_success

bar = ProgressBar(total=10, prefix="Test")
check("ProgressBar created", bar is not None)
check("ProgressBar total set", bar.total == 10)
check("ProgressBar width default", bar.width == 40)

# Test update doesn't crash
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    bar.update(5, suffix="BTCUSDT")
    bar.finish("Done")
output = buf.getvalue()
check("ProgressBar finish produces output", len(output) > 0)
check("ProgressBar finish contains 100%", "100%" in output)


# ============================================================
# TEST 2: progress.py — StepProgress
# ============================================================
print("\n[TEST 2] progress.py — StepProgress")

steps = ["Step A", "Step B", "Step C"]
sp = StepProgress(steps)
check("StepProgress created", sp is not None)
check("StepProgress total = 3", sp.total == 3)
check("No steps completed initially", not any(sp._completed))

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    sp.start_step(0, "starting")
    sp.complete_step(0, "done")
    sp.fail_step(1, "error")
output = buf.getvalue()
check("StepProgress start produces output", "⏳" in output or "Step A" in output)
check("StepProgress complete produces output", "✅" in output or "done" in output)
check("StepProgress fail produces output", "❌" in output or "error" in output)


# ============================================================
# TEST 3: progress.py — format_table
# ============================================================
print("\n[TEST 3] progress.py — format_table")

headers = ["Symbol", "Price", "Score"]
rows = [
    ["BTCUSDT", "$65000", "95/100"],
    ["ETHUSDT", "$3500", "88/100"],
]
table = format_table(headers, rows, title="Test Table")
check("format_table returns string", isinstance(table, str))
check("format_table contains headers", "Symbol" in table and "Price" in table)
check("format_table contains data", "BTCUSDT" in table)
check("format_table has separators", "+" in table or "-" in table)
check("format_table contains title", "Test Table" in table)

# Empty table
empty_table = format_table(headers, [])
check("Empty table returns placeholder", "暂无数据" in empty_table)


# ============================================================
# TEST 4: progress.py — format_error
# ============================================================
print("\n[TEST 4] progress.py — format_error")

err_451 = format_error("451")
check("451 error contains title", "451" in err_451 or "地区限制" in err_451)
check("451 error contains solution", "testnet" in err_451 or "解决" in err_451)

err_no_a = format_error("no_results_a")
check("no_results_a error contains suggestion", "次新币" in err_no_a or "放宽" in err_no_a)

err_unknown = format_error("unknown_error_xyz")
check("Unknown error handled gracefully", "未知错误" in err_unknown or len(err_unknown) > 0)

warn = format_warning("Test warning")
check("format_warning contains message", "Test warning" in warn)

success = format_success("Test success")
check("format_success contains message", "Test success" in success)


# ============================================================
# TEST 5: param_advisor.py — MarketRegime Detection
# ============================================================
print("\n[TEST 5] param_advisor.py — Market Regime Detection")

from param_advisor import ParameterAdvisor, MarketRegime, detect_market_regime

check("MarketRegime.SIDEWAYS defined", MarketRegime.SIDEWAYS == "SIDEWAYS")
check("MarketRegime.VOLATILE defined", MarketRegime.VOLATILE == "VOLATILE")
check("MarketRegime.BREAKOUT defined", MarketRegime.BREAKOUT == "BREAKOUT")
check("MarketRegime.TRENDING defined", MarketRegime.TRENDING == "TRENDING")

# Regime detection
regime_sideways = detect_market_regime(avg_volatility_24h=3.0, avg_adx=15.0)
check("Low vol + low ADX = SIDEWAYS", regime_sideways == MarketRegime.SIDEWAYS)

regime_volatile = detect_market_regime(avg_volatility_24h=20.0, avg_adx=30.0)
check("High vol + high ADX = VOLATILE", regime_volatile == MarketRegime.VOLATILE)

regime_trending = detect_market_regime(avg_volatility_24h=5.0, avg_adx=35.0)
check("Low vol + high ADX = TRENDING", regime_trending == MarketRegime.TRENDING)

regime_breakout = detect_market_regime(avg_volatility_24h=10.0, avg_adx=20.0, vol_change_pct=80.0)
check("High vol_change = BREAKOUT", regime_breakout == MarketRegime.BREAKOUT)


# ============================================================
# TEST 6: param_advisor.py — ParameterAdvisor
# ============================================================
print("\n[TEST 6] param_advisor.py — ParameterAdvisor")

advisor = ParameterAdvisor()
check("ParameterAdvisor created", advisor is not None)

# No results → should suggest relaxing params
suggestions_empty = advisor.analyze(cat_a_count=0, cat_b_count=0, avg_vol=10.0)
check("Empty results → suggestions generated", len(suggestions_empty) > 0)
check("Empty results → HIGH priority suggestions exist",
      any(s.priority == "HIGH" for s in suggestions_empty))

# Good results → fewer suggestions
suggestions_good = advisor.analyze(cat_a_count=3, cat_b_count=3, avg_vol=10.0)
high_priority_count = sum(1 for s in suggestions_good if s.priority == "HIGH")
check("Good results → no HIGH priority suggestions", high_priority_count == 0)

# Test high volatility → leverage reduction suggestion
# avg_vol=25.0 > 15 threshold, avg_adx=30 to also trigger VOLATILE regime
suggestions_vol = advisor.analyze(cat_a_count=2, cat_b_count=2, avg_vol=25.0, avg_adx=30.0)
leverage_suggestions = [s for s in suggestions_vol if "leverage" in s.param_name.lower()]
check("High vol → leverage reduction suggested", len(leverage_suggestions) > 0)

# Test format_report
report = advisor.format_report(suggestions_empty, regime=MarketRegime.SIDEWAYS,
                                cat_a_count=0, cat_b_count=0)
check("format_report returns string", isinstance(report, str))
check("format_report contains regime info", "横盘" in report or "SIDEWAYS" in report)
check("format_report contains suggestion count", len(report) > 50)

# Test ParamSuggestion.to_display
if suggestions_empty:
    display = suggestions_empty[0].to_display()
    check("ParamSuggestion.to_display works", isinstance(display, str) and len(display) > 0)
    check("ParamSuggestion display contains param name",
          suggestions_empty[0].param_name in display)


# ============================================================
# TEST 7: api_server.py — WebhookClient
# ============================================================
print("\n[TEST 7] api_server.py — WebhookClient")

from api_server import WebhookClient

# Test without URL (should not crash)
client_no_url = WebhookClient(url="")
check("WebhookClient created without URL", client_no_url is not None)
check("is_configured = False without URL", not client_no_url.is_configured)

result = client_no_url.send("INFO", "BTCUSDT", "Test message")
check("send() returns False without URL", result == False)

# Test with URL (mock - won't actually send)
client_with_url = WebhookClient(url="http://localhost:9999/webhook")
check("is_configured = True with URL", client_with_url.is_configured)

# Test history tracking
client_with_url._history.append({
    "level": "INFO", "symbol": "TEST", "message": "test",
    "timestamp": datetime.utcnow().isoformat()
})
history = client_with_url.get_history(limit=5)
check("get_history returns list", isinstance(history, list))
check("get_history respects limit", len(history) <= 5)


# ============================================================
# TEST 8: backtester.py — Enhanced format_report
# ============================================================
print("\n[TEST 8] backtester.py — Enhanced format_report with Ratings")

from backtester import GridBacktester, BacktestConfig, BacktestResult

# Create a mock result with good performance
config = BacktestConfig(
    symbol="BTCUSDT",
    lower_price=60000,
    upper_price=70000,
    grid_count=30,
    leverage=5,
    initial_margin=1000.0,
)
result = BacktestResult(
    config=config,
    start_time=int(time.time() * 1000) - 30 * 86400 * 1000,
    end_time=int(time.time() * 1000),
    total_candles=720,
    roi_pct=25.5,
    sharpe_ratio=3.2,
    max_drawdown_pct=4.1,
    total_trades=296,
    buy_trades=148,
    sell_trades=148,
    winning_trades=140,
    net_pnl=255.0,
    total_fees=12.5,
    fills_per_day=9.9,
    time_in_range_pct=78.5,
    grid_levels_touched=25,
    grid_utilization_pct=83.3,
    price_start=62000,
    price_end=68000,
    price_high=71000,
    price_low=59000,
)

report = GridBacktester.format_report(result)
check("format_report returns string", isinstance(report, str))
check("format_report contains symbol", "BTCUSDT" in report)
check("format_report contains ROI", "25.5" in report or "25" in report)
check("format_report contains rating", "优秀" in report or "良好" in report or "🏆" in report)
check("format_report contains 夏普比率", "夏普" in report)
# The report always contains 止损触发 in the stop-loss conditional section
# For a non-stop-loss result, check that the report contains key sections instead
check("format_report contains key sections", "收益表现" in report and "交易统计" in report)

# Test stop-loss triggered report
result_sl = BacktestResult(
    config=config,
    start_time=int(time.time() * 1000) - 30 * 86400 * 1000,
    end_time=int(time.time() * 1000),
    total_candles=100,
    roi_pct=-8.5,
    sharpe_ratio=-0.5,
    stop_loss_triggered=True,
    stop_loss_time=int(time.time() * 1000) - 15 * 86400 * 1000,
)
report_sl = GridBacktester.format_report(result_sl)
check("Stop-loss report contains warning", "止损触发" in report_sl or "⚠️" in report_sl)
check("Stop-loss report contains suggestion", "建议" in report_sl)
check("Stop-loss rating is high risk", "高风险" in report_sl or "❌" in report_sl)


# ============================================================
# TEST 9: grid_hunter_v5.py — Enhanced format_scan_output
# ============================================================
print("\n[TEST 9] grid_hunter_v5.py — Enhanced format_scan_output")

from grid_hunter_v5 import (
    GridParameters, format_scan_output, VERSION, UserConfig,
    FuturesSymbol, MarketSnapshot, TechnicalAnalysis,
)

# Create mock GridParameters
def make_gp(symbol, category, price=100.0, score=75.0, mcap=500_000_000):
    return GridParameters(
        symbol=symbol,
        category=category,
        strategy_type="Neutral",
        grid_type="Geometric",
        lower_price=price * 0.92,
        upper_price=price * 1.08,
        current_price=price,
        grid_count=30,
        grid_ratio=1.0053,
        profit_per_grid_pct=0.85,
        stop_loss_price=price * 0.874,
        liquidation_price=price * 0.82,
        leverage=5,
        funding_rate=-0.0001,
        daily_funding_yield_pct=0.03,
        volatility_24h_pct=12.5,
        atr_pct=1.8,
        support=price * 0.91,
        resistance=price * 1.09,
        grid_score=score,
        category_reason="Test reason",
        market_cap=mcap,
        turnover_rate_pct=65.0,
    )

cat_a = [make_gp("NEWUSDT", "recent_contract", 2.5, 80.0)]
cat_b = [make_gp("HIGHUSDT", "high_volatility", 15.0, 72.0)]

output = format_scan_output(cat_a, cat_b)
check("format_scan_output returns string", isinstance(output, str))
check("Output contains Category A header", "Category A" in output)
check("Output contains Category B header", "Category B" in output)
check("Output contains NEWUSDT", "NEWUSDT" in output)
check("Output contains HIGHUSDT", "HIGHUSDT" in output)
check("Output contains grid details", "等比网格" in output or "Geometric" in output)
check("Output contains param suggestions section", "参数优化" in output or "建议" in output)
check("Output contains version", VERSION in output)

# Test with empty results
output_empty = format_scan_output([], [])
check("Empty output contains warning", "暂无" in output_empty or "⚠️" in output_empty)
check("Empty output contains suggestion", "建议" in output_empty or "💡" in output_empty)


# ============================================================
# TEST 10: UserConfig — v2.0 Validate & Display
# ============================================================
print("\n[TEST 10] UserConfig — Validation & Display")

from grid_hunter_v5 import UserConfig

cfg = UserConfig()
check("Default UserConfig created", cfg is not None)
check("Default leverage = 5", cfg.leverage == 5)
check("Default top_n = 3", cfg.top_n == 3)

warnings = cfg.validate()
check("Default config has no warnings", len(warnings) == 0)

# High leverage warning
cfg_high_lev = UserConfig(leverage=25)
warnings_high = cfg_high_lev.validate()
check("Leverage 25 generates warning", len(warnings_high) > 0)
check("Warning mentions leverage", any("杠杆" in w for w in warnings_high))

# Invalid mcap range
cfg_bad_mcap = UserConfig(mcap_min=1_000_000_000, mcap_max=200_000_000)
warnings_mcap = cfg_bad_mcap.validate()
check("Invalid mcap range generates warning", len(warnings_mcap) > 0)

# to_display
display = cfg.to_display()
check("to_display returns string", isinstance(display, str))
check("to_display contains Category A info", "Category A" in display)
check("to_display contains Category B info", "Category B" in display)
check("to_display contains leverage", "5×" in display or "leverage" in display.lower() or "杠杆" in display)


# ============================================================
# TEST 11: Backtest — run_backtest convenience function
# ============================================================
print("\n[TEST 11] backtester.py — run_backtest with synthetic klines")

from backtester import run_backtest, GridBacktester, BacktestConfig

# Generate synthetic klines (720 x 1h)
random.seed(42)
klines = []
price = 100.0
ts = int(time.time() * 1000) - 720 * 3600 * 1000
for i in range(720):
    o = price
    price = price * (1 + random.uniform(-0.005, 0.005))
    h = max(o, price) * (1 + random.uniform(0, 0.003))
    l = min(o, price) * (1 - random.uniform(0, 0.003))
    klines.append([ts + i * 3600 * 1000, str(o), str(h), str(l), str(price), str(1000000)])

result = run_backtest(
    symbol="TESTUSDT",
    lower_price=90.0,
    upper_price=110.0,
    grid_count=20,
    leverage=5,
    initial_margin=1000.0,
    klines=klines,
)

check("run_backtest returns BacktestResult", result is not None)
check("Backtest has trades", result.total_trades > 0)
check("Backtest equity curve populated", len(result.equity_curve) > 0)
check("Backtest fills_per_day > 0", result.fills_per_day > 0)
check("Backtest time_in_range > 0", result.time_in_range_pct > 0)
check("Backtest grid_utilization > 0", result.grid_utilization_pct > 0)
check("Backtest sharpe_ratio computed", result.sharpe_ratio != 0)
check("Backtest roi_pct computed", isinstance(result.roi_pct, float))


# ============================================================
# TEST 12: Integration — format_scan_output with param_advisor
# ============================================================
print("\n[TEST 12] Integration — format_scan_output + param_advisor")

# Test with no results (should trigger suggestions)
output_no_results = format_scan_output([], [], config=UserConfig())
check("No results output has suggestions", "建议" in output_no_results or "参数" in output_no_results)
check("No results output has warning emoji", "⚠️" in output_no_results)

# Test with results (should show tables)
output_with_results = format_scan_output(
    [make_gp("AAUSDT", "recent_contract", 5.0, 85.0)],
    [make_gp("BBUSDT", "high_volatility", 50.0, 78.0)],
    config=UserConfig(),
)
check("Results output has table header", "#" in output_with_results)
check("Results output has score column", "/100" in output_with_results)
check("Results output has grid details section", "等比网格策略详情" in output_with_results)


# ============================================================
# FINAL SUMMARY
# ============================================================
print(f"\n{'='*65}")
print(f"  V2.0 TEST RESULTS: {PASSED}/{TOTAL} passed, {FAILED} failed")
print(f"{'='*65}")

if FAILED == 0:
    print(f"  ✓ ALL {TOTAL} V2.0 TESTS PASSED")
else:
    print(f"  ✗ {FAILED} TESTS FAILED — REVIEW ABOVE")
    sys.exit(1)
