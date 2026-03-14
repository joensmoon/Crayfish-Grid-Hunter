#!/usr/bin/env python3
"""
Crayfish Grid Hunter v5.2 — Comprehensive Test Suite
=====================================================
Tests all core algorithms with mock data (no live API required).

Run:
    python3 test_grid_hunter.py

Expected output: All tests PASSED
"""

import math
import random
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, "skills/crayfish-grid-hunter")
from grid_hunter_v5 import (
    VERSION,
    CONTRACT_RECENT_DAYS,
    VOLUME_SHRINK_RATIO,
    ATR_SIDEWAYS_PCT,
    BB_WIDTH_SIDEWAYS,
    ADX_SIDEWAYS,
    MCAP_MIN,
    MCAP_MAX,
    TURNOVER_MIN,
    HIGH_VOL_RV_MIN,
    MAKER_FEE,
    MIN_GRID_PROFIT,
    FuturesSymbol,
    MarketSnapshot,
    TokenMarketData,
    TechnicalAnalysis,
    GridParameters,
    calculate_geometric_grid,
    screen_recent_contracts,
    screen_high_volatility,
    format_scan_output,
)
from monitor import (
    AlertLevel, GridPerformanceMonitor, GridPosition, MonitorThresholds,
    check_funding_and_liquidation, create_monitor,
)

random.seed(42)
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


def now_ms():
    return int(time.time() * 1000)


def make_symbol(name, base, age_days):
    return FuturesSymbol(
        symbol=f"{name}USDT", base_asset=base,
        onboard_date=now_ms() - int(age_days * 86400 * 1000),
        contract_type="PERPETUAL", price_precision=4,
        qty_precision=3, tick_size=0.01, step_size=0.001,
    )


def make_snapshot(symbol, price=100.0, vol=1000000, qvol=50000000,
                  oi=10000000, funding=-0.001, high=None, low=None):
    h = high or price * 1.02
    l = low or price * 0.98
    return MarketSnapshot(
        symbol=symbol, mark_price=price, index_price=price,
        last_price=price, price_change_pct_24h=2.0,
        volume_24h=vol, quote_volume_24h=qvol,
        open_interest=oi, funding_rate=funding,
        next_funding_time=0, high_24h=h, low_24h=l,
    )


def make_tech_sideways(symbol, closes=None, volumes=None):
    """Create TechnicalAnalysis with sideways + volume shrinkage."""
    random.seed(42)
    if closes is None:
        closes = [100 + random.uniform(-0.5, 0.5) for _ in range(30)]
    highs = [c + random.uniform(0.2, 0.8) for c in closes]
    lows = [c - random.uniform(0.2, 0.8) for c in closes]
    if volumes is None:
        volumes = [1000000 + random.uniform(-50000, 50000) for _ in range(29)] + [300000]
    return TechnicalAnalysis(symbol, closes, highs, lows, volumes)


def make_tech_volatile(symbol, vol_factor=5.0):
    """Create TechnicalAnalysis with high volatility."""
    random.seed(99)
    closes = [100]
    for _ in range(29):
        closes.append(closes[-1] * (1 + random.uniform(-0.03, 0.03) * vol_factor))
    highs = [c * (1 + random.uniform(0.01, 0.03)) for c in closes]
    lows = [c * (1 - random.uniform(0.01, 0.03)) for c in closes]
    volumes = [5000000 + random.uniform(-500000, 500000) for _ in range(30)]
    return TechnicalAnalysis(symbol, closes, highs, lows, volumes)


# ============================================================
# TEST 1: FuturesSymbol — Contract Age (≤90 days = recent)
# ============================================================
print(f"\n{'='*60}")
print(f"  CRAYFISH GRID HUNTER v{VERSION} — TEST SUITE")
print(f"{'='*60}")

print("\n[TEST 1] FuturesSymbol — Contract Age & Classification")

sym_30d = make_symbol("NEW30", "NEW30", 30)
check("30-day contract is recent",
      sym_30d.is_recent_contract,
      f"age={sym_30d.contract_age_days:.1f}")

sym_89d = make_symbol("NEW89", "NEW89", 89)
check("89-day contract is recent",
      sym_89d.is_recent_contract,
      f"age={sym_89d.contract_age_days:.1f}")

sym_90d = make_symbol("EDGE90", "EDGE90", 90)
check("90-day contract is recent (exact boundary)",
      sym_90d.is_recent_contract,
      f"age={sym_90d.contract_age_days:.1f}")

sym_91d = make_symbol("OLD91", "OLD91", 91)
check("91-day contract is NOT recent",
      not sym_91d.is_recent_contract,
      f"age={sym_91d.contract_age_days:.1f}")

sym_365d = make_symbol("OLD365", "OLD365", 365)
check("365-day contract is NOT recent",
      not sym_365d.is_recent_contract,
      f"age={sym_365d.contract_age_days:.1f}")

check(f"CONTRACT_RECENT_DAYS = {CONTRACT_RECENT_DAYS}",
      CONTRACT_RECENT_DAYS == 90)


# ============================================================
# TEST 2: TechnicalAnalysis — Sideways Indicators
# ============================================================
print("\n[TEST 2] TechnicalAnalysis — Sideways Market Indicators")

tech_sw = make_tech_sideways("SIDEWAYS")
check("ATR(14) < 5% for sideways data",
      tech_sw.atr_14_pct < 5.0,
      f"ATR={tech_sw.atr_14_pct:.4f}%")

check("BB width < 10% for sideways data",
      tech_sw.bb_width_pct < 10.0,
      f"BB_width={tech_sw.bb_width_pct:.4f}%")

check("ADX computed and reasonable",
      0 <= tech_sw.adx_14 < 100,
      f"ADX={tech_sw.adx_14:.2f}")

check("RV computed and > 0",
      tech_sw.realized_volatility_pct > 0,
      f"RV={tech_sw.realized_volatility_pct:.2f}%")

check("Volume shrinkage ratio < 0.5",
      tech_sw.volume_shrinkage_ratio < 0.5,
      f"ratio={tech_sw.volume_shrinkage_ratio:.4f}")

tech_noshrink = make_tech_sideways("NOSHRINK", volumes=[1000000] * 30)
check("Volume ratio ~1.0 with constant volume",
      0.9 < tech_noshrink.volume_shrinkage_ratio < 1.1,
      f"ratio={tech_noshrink.volume_shrinkage_ratio:.4f}")

check("Support = min(lows[-20:])",
      tech_sw.support_level == min(tech_sw.lows[-20:]),
      f"support={tech_sw.support_level:.4f}")

check("Resistance = max(highs[-20:])",
      tech_sw.resistance_level == max(tech_sw.highs[-20:]),
      f"resistance={tech_sw.resistance_level:.4f}")


# ============================================================
# TEST 3: Bollinger Band — Standard 20-Period Precision
# ============================================================
print("\n[TEST 3] Bollinger Band — Standard 20-Period Precision")

known_closes = list(range(1, 31))
tech_bb = TechnicalAnalysis("BBTEST", known_closes,
    [c + 0.5 for c in known_closes], [c - 0.5 for c in known_closes])
expected_sma = sum(range(11, 31)) / 20
manual_std = math.sqrt(sum((x - expected_sma) ** 2 for x in range(11, 31)) / 20)
check("BB lower uses last 20 closes",
      abs(tech_bb.bb_lower - (expected_sma - 2 * manual_std)) < 0.0001,
      f"got={tech_bb.bb_lower:.4f}, expected={expected_sma - 2 * manual_std:.4f}")
check("BB upper uses last 20 closes",
      abs(tech_bb.bb_upper - (expected_sma + 2 * manual_std)) < 0.0001,
      f"got={tech_bb.bb_upper:.4f}, expected={expected_sma + 2 * manual_std:.4f}")

# Verify BB width formula
expected_bb_width = (4 * manual_std) / expected_sma * 100
check("BB width matches manual calculation",
      abs(tech_bb.bb_width_pct - expected_bb_width) < 0.0001,
      f"got={tech_bb.bb_width_pct:.6f}, expected={expected_bb_width:.6f}")


# ============================================================
# TEST 4: TokenMarketData — Market Cap & Turnover
# ============================================================
print("\n[TEST 4] TokenMarketData — Market Cap & Turnover")

td1 = TokenMarketData("TEST", 500_000_000, 300_000_000)
check("Turnover rate = vol/mcap = 0.6",
      abs(td1.turnover_rate - 0.6) < 0.001,
      f"got={td1.turnover_rate}")

td_zero = TokenMarketData("ZERO", 0, 100_000_000)
check("Turnover = 0 when mcap = 0",
      td_zero.turnover_rate == 0.0)

check(f"MCAP_MIN = ${MCAP_MIN/1e6:.0f}M",
      MCAP_MIN == 200_000_000)
check(f"MCAP_MAX = ${MCAP_MAX/1e6:.0f}M",
      MCAP_MAX == 1_000_000_000)
check(f"TURNOVER_MIN = {TURNOVER_MIN*100:.0f}%",
      TURNOVER_MIN == 0.50)


# ============================================================
# TEST 5: Geometric Grid — Core Calculation
# ============================================================
print("\n[TEST 5] Geometric Grid — Core Calculation")

snap_grid = make_snapshot("GRIDTEST", price=2.5, high=2.75, low=2.30, funding=-0.00012)
tech_grid = TechnicalAnalysis("GRIDTEST",
    closes=[2.3 + i * 0.01 for i in range(30)],
    highs=[2.3 + i * 0.01 + 0.05 for i in range(30)],
    lows=[2.3 + i * 0.01 - 0.05 for i in range(30)],
    volumes=[1000000] * 30,
)
gp = calculate_geometric_grid("GRIDTEST", "high_volatility", snap_grid, tech_grid, 75.0, "Test")

check("Grid type is Geometric", gp.grid_type == "Geometric")
check("Strategy type is Neutral", gp.strategy_type == "Neutral")
check("Price within grid range",
      gp.lower_price < gp.current_price < gp.upper_price,
      f"lower={gp.lower_price}, price={gp.current_price}, upper={gp.upper_price}")
check("Grid count > 0", gp.grid_count > 0, f"count={gp.grid_count}")
check("Grid ratio > 1", gp.grid_ratio > 1.0, f"ratio={gp.grid_ratio}")

# Verify geometric property: r^n = upper/lower
r_n = gp.grid_ratio ** gp.grid_count
actual_ratio = gp.upper_price / gp.lower_price
check("Geometric property: r^n ≈ upper/lower",
      abs(r_n - actual_ratio) < 0.001,
      f"r^n={r_n:.8f}, upper/lower={actual_ratio:.8f}")

# Verify equal ratio across all grids
levels = [gp.lower_price * (gp.grid_ratio ** i) for i in range(gp.grid_count + 1)]
ratios = [levels[i + 1] / levels[i] for i in range(len(levels) - 1)]
ratio_variance = max(ratios) - min(ratios)
check("Equal ratio across all grids (variance < 1e-10)",
      ratio_variance < 1e-10, f"variance={ratio_variance:.2e}")

check("Per-grid profit ≥ 0.8%",
      gp.profit_per_grid_pct >= 0.8,
      f"profit={gp.profit_per_grid_pct:.4f}%")

check("Stop-loss = lower × 0.95",
      abs(gp.stop_loss_price - round(gp.lower_price * 0.95, 6)) < 0.01,
      f"stop={gp.stop_loss_price}, expected={gp.lower_price * 0.95}")

check("Liquidation price < stop-loss",
      gp.liquidation_price < gp.stop_loss_price,
      f"liq={gp.liquidation_price}, stop={gp.stop_loss_price}")


# ============================================================
# TEST 5b: Minimum Profit Enforcement
# ============================================================
print("\n[TEST 5b] Minimum Profit Enforcement (narrow range)")

snap_narrow = make_snapshot("NARROW", price=100.0, high=100.5, low=99.5)
random.seed(77)
tech_narrow = TechnicalAnalysis("NARROW",
    closes=[100.0 + random.uniform(-0.1, 0.1) for _ in range(30)],
    highs=[100.5 for _ in range(30)], lows=[99.5 for _ in range(30)],
    volumes=[1000000] * 30,
)
gp_narrow = calculate_geometric_grid("NARROW", "recent_contract", snap_narrow, tech_narrow, 60.0, "Narrow")
check("Narrow range: profit ≥ 0.8%",
      gp_narrow.profit_per_grid_pct >= 0.8,
      f"profit={gp_narrow.profit_per_grid_pct:.4f}%")
check("Narrow range: grid count reduced",
      gp_narrow.grid_count < 20,
      f"count={gp_narrow.grid_count}")


# ============================================================
# TEST 6: Category A — 次新币横盘类
# ============================================================
print("\n[TEST 6] Category A — 次新币横盘类 (Recent Contract Listings)")

symbols_a = [
    make_symbol("RECENT1", "RECENT1", 20),
    make_symbol("RECENT2", "RECENT2", 45),
    make_symbol("RECENT3", "RECENT3", 80),
    make_symbol("OLD1", "OLD1", 100),
    make_symbol("OLD2", "OLD2", 365),
]

snaps_a, techs_a = {}, {}
for s in symbols_a:
    snaps_a[s.symbol] = make_snapshot(s.symbol, price=50.0)
    if "OLD" in s.symbol:
        techs_a[s.symbol] = make_tech_sideways(s.symbol, volumes=[1000000] * 30)
    else:
        techs_a[s.symbol] = make_tech_sideways(s.symbol)

results_a = screen_recent_contracts(symbols_a, snaps_a, techs_a, top_n=3)
check("Cat A returns results", len(results_a) > 0, f"got {len(results_a)}")
check("All Cat A are ≤90 days",
      all(sym.contract_age_days <= CONTRACT_RECENT_DAYS for sym, _, _, _, _ in results_a))
check("OLD1USDT excluded (>90 days)",
      "OLD1USDT" not in [r[0].symbol for r in results_a])
check("OLD2USDT excluded (>90 days)",
      "OLD2USDT" not in [r[0].symbol for r in results_a])
check("Results sorted by score (descending)",
      all(results_a[i][3] >= results_a[i + 1][3] for i in range(len(results_a) - 1)))

# Verify volume shrinkage is required
symbols_ns = [make_symbol("NOSHRINK", "NOSHRINK", 30)]
snaps_ns = {s.symbol: make_snapshot(s.symbol) for s in symbols_ns}
techs_ns = {s.symbol: make_tech_sideways(s.symbol, volumes=[1000000] * 30) for s in symbols_ns}
results_ns = screen_recent_contracts(symbols_ns, snaps_ns, techs_ns)
check("Cat A rejects recent contract WITHOUT volume shrinkage",
      len(results_ns) == 0, f"got {len(results_ns)} (expected 0)")


# ============================================================
# TEST 7: Category B — 高波动套利类
# ============================================================
print("\n[TEST 7] Category B — 高波动套利类 (High Volatility Arbitrage)")

sym_b = [
    make_symbol("MEME1", "MEME1", 200),
    make_symbol("MEME2", "MEME2", 150),
    make_symbol("BLUE1", "BLUE1", 500),
    make_symbol("TINY1", "TINY1", 100),
]

snap_b = {
    "MEME1USDT": make_snapshot("MEME1USDT", price=5.0, qvol=400_000_000, high=5.5, low=4.5),
    "MEME2USDT": make_snapshot("MEME2USDT", price=2.0, qvol=300_000_000, high=2.3, low=1.7),
    "BLUE1USDT": make_snapshot("BLUE1USDT", price=100.0, qvol=500_000_000, high=105, low=95),
    "TINY1USDT": make_snapshot("TINY1USDT", price=0.01, qvol=5_000_000, high=0.012, low=0.008),
}

tech_b = {s.symbol: make_tech_volatile(s.symbol) for s in sym_b}

token_b = {
    "MEME1": TokenMarketData("MEME1", 500_000_000, 400_000_000),
    "MEME2": TokenMarketData("MEME2", 300_000_000, 200_000_000),
    "BLUE1": TokenMarketData("BLUE1", 5_000_000_000, 500_000_000),
    "TINY1": TokenMarketData("TINY1", 50_000_000, 30_000_000),
}

results_b = screen_high_volatility(sym_b, snap_b, tech_b, token_b, top_n=3)
check("Cat B returns results", len(results_b) > 0, f"got {len(results_b)}")
check("BLUE1 excluded (mcap $5B > $1B)",
      "BLUE1USDT" not in [r[0].symbol for r in results_b])
check("TINY1 excluded (mcap $50M < $200M)",
      "TINY1USDT" not in [r[0].symbol for r in results_b])

# Low turnover rejection
sym_lt = [make_symbol("LOWTURN", "LOWTURN", 200)]
snap_lt = {"LOWTURNUSDT": make_snapshot("LOWTURNUSDT", price=10, qvol=50_000_000)}
tech_lt = {"LOWTURNUSDT": make_tech_volatile("LOWTURNUSDT")}
token_lt = {"LOWTURN": TokenMarketData("LOWTURN", 500_000_000, 100_000_000)}
results_lt = screen_high_volatility(sym_lt, snap_lt, tech_lt, token_lt)
check("Cat B rejects low turnover (<50%)",
      len(results_lt) == 0, f"got {len(results_lt)} (expected 0)")

# No market cap data rejection
sym_nomc = [make_symbol("NOMC", "NOMC", 200)]
snap_nomc = {"NOMCUSDT": make_snapshot("NOMCUSDT", price=10, qvol=100_000_000)}
tech_nomc = {"NOMCUSDT": make_tech_volatile("NOMCUSDT")}
token_nomc = {}  # No market cap data
results_nomc = screen_high_volatility(sym_nomc, snap_nomc, tech_nomc, token_nomc)
check("Cat B rejects symbols without market cap data",
      len(results_nomc) == 0, f"got {len(results_nomc)} (expected 0)")


# ============================================================
# TEST 8: Funding Rate & Risk Alerts
# ============================================================
print("\n[TEST 8] Funding Rate & Risk Alerts")

snap_neg = make_snapshot("NEGFUND", funding=-0.0012)
tech_neg = make_tech_sideways("NEGFUND")
gp_neg = calculate_geometric_grid("NEGFUND", "recent_contract", snap_neg, tech_neg, 70, "test")
check("Negative funding: daily yield > 0",
      gp_neg.daily_funding_yield_pct > 0,
      f"yield={gp_neg.daily_funding_yield_pct}%")
display_neg = gp_neg.to_display()
check("Negative funding display mentions '多头网格'",
      "多头网格" in display_neg)

snap_pos = make_snapshot("POSFUND", funding=0.002)
gp_pos = calculate_geometric_grid("POSFUND", "high_volatility", snap_pos, tech_neg, 70, "test",
                                   market_cap=500e6, turnover_rate=0.8)
display_pos = gp_pos.to_display()
check("Positive funding display mentions '空头网格'",
      "空头网格" in display_pos)

snap_neutral = make_snapshot("NEUTRAL", funding=0.0001)
gp_neutral = calculate_geometric_grid("NEUTRAL", "recent_contract", snap_neutral, tech_neg, 70, "test")
display_neutral = gp_neutral.to_display()
check("Neutral funding display mentions '中性'",
      "中性" in display_neutral)


# ============================================================
# TEST 9: Monitor — Existing Alert Checks (v4.4 regression)
# ============================================================
print("\n[TEST 9] Monitor — Existing Alert Checks (v4.4 regression)")

monitor = create_monitor(pnl_loss_critical_pct=-5.0, boundary_proximity_critical_pct=3.0,
    stop_loss_proximity_critical_pct=2.0, volume_spike_multiplier=2.5)
pos = GridPosition(
    symbol="BTCUSDT", grid_lower=68000.0, grid_upper=74000.0, grid_count=30,
    entry_price=71000.0, current_price=73800.0, stop_loss=66640.0, invested_usdt=1000.0,
    realized_pnl=12.5, unrealized_pnl=8.3, total_fills=18, total_orders=30,
    start_time=datetime.now() - timedelta(hours=6),
)
monitor.register_position(pos)
monitor.update_position("BTCUSDT", current_price=73800.0, realized_pnl=12.5, unrealized_pnl=8.3,
    current_volume=28000.0, avg_volume_24h=10000.0)
monitor.record_api_call("fapi/v1/klines", latency_ms=120, success=True)
monitor.record_api_call("fapi/v1/klines", latency_ms=1200, success=False)
monitor.mark_fallback_active("fapi/v1/klines", True)
alerts_v4 = monitor.run_checks()
check("Monitor generates alerts", len(alerts_v4) > 0)
check("CRITICAL boundary alert",
      any(a.level == AlertLevel.CRITICAL and "boundary" in a.message.lower() for a in alerts_v4))
check("CRITICAL volume spike alert",
      any(a.level == AlertLevel.CRITICAL and "volume" in a.message.lower() for a in alerts_v4))
report = monitor.format_report()
check("Report contains BTCUSDT", "BTCUSDT" in report)


# ============================================================
# TEST 10: Futures Monitor — Funding & Liquidation
# ============================================================
print("\n[TEST 10] Futures Monitor — Funding & Liquidation")

alerts_10a = check_funding_and_liquidation("BTCUSDT", 70000, -0.00012, 50000, 65000, "neutral")
check("10a: Negative funding -> INFO earns",
      any(a.level == AlertLevel.INFO and "earns" in a.message for a in alerts_10a))

alerts_10b = check_funding_and_liquidation("ETHUSDT", 2400, 0.0001, 1800, 2500, "long")
check("10b: Stop-loss breach -> CRITICAL",
      any(a.level == AlertLevel.CRITICAL and "stop-loss" in a.message for a in alerts_10b))

alerts_10c = check_funding_and_liquidation("SOLUSDT", 105, 0.0001, 100, 90, "long")
check("10c: Near liquidation -> CRITICAL",
      any("liquidation" in a.message.lower() for a in alerts_10c))

alerts_10d = check_funding_and_liquidation("XYZUSDT", 5.0, 0.006, 2.0, 3.0, "long")
check("10d: Extreme funding -> CRITICAL",
      any(a.level == AlertLevel.CRITICAL and "EXTREME" in a.message for a in alerts_10d))

alerts_10e = check_funding_and_liquidation("ABCUSDT", 10.0, 0.004, 5.0, 7.0, "long")
check("10e: High funding -> HIGH",
      any(a.level == AlertLevel.HIGH and "High funding" in a.message for a in alerts_10e))

alerts_10f = check_funding_and_liquidation("DEFUSDT", 10.0, 0.0002, 5.0, 7.0, "short")
check("10f: Positive funding short -> INFO",
      any(a.level == AlertLevel.INFO and "short grid earns" in a.message for a in alerts_10f))


# ============================================================
# TEST 11: Grid Display Format
# ============================================================
print("\n[TEST 11] Grid Display Format")

snap_disp = make_snapshot("DISPLAY", price=50.0, funding=-0.0008, high=52, low=48)
tech_disp = make_tech_sideways("DISPLAY")
gp_disp = calculate_geometric_grid(
    "DISPLAYUSDT", "high_volatility", snap_disp, tech_disp, 85.0,
    "市值$500M; 换手率85%; RV=22.5%/yr",
    market_cap=500_000_000, turnover_rate=0.85,
)
display = gp_disp.to_display()

check("Display contains symbol", "DISPLAYUSDT" in display)
check("Display contains '合约中性网格'", "合约中性网格" in display)
check("Display contains 'Geometric'", "Geometric" in display)
check("Display contains '硬止损位'", "硬止损位" in display)
check("Display contains '强平价估算'", "强平价估算" in display)
check("Display contains 'Funding提醒'", "Funding提醒" in display)
check("Display contains '市值'", "市值" in display)
check("Display contains '换手率'", "换手率" in display)
check("Display contains '网格评分'", "网格评分" in display)


# ============================================================
# TEST 12: Output Formatting
# ============================================================
print("\n[TEST 12] Output Formatting")

cat_a_out = [gp]
cat_b_out = [gp_disp]
output = format_scan_output(cat_a_out, cat_b_out)

check("Output contains '次新币横盘类'", "次新币横盘类" in output)
check("Output contains '高波动套利类'", "高波动套利类" in output)
check("Output contains version", VERSION in output)
check("Output contains '策略类型'", "策略类型" in output)


# ============================================================
# Summary
# ============================================================
print(f"\n{'='*60}")
print(f"  TEST RESULTS: {PASSED}/{TOTAL} passed, {FAILED} failed")
print(f"  Version: v{VERSION} — {datetime.now().strftime('%Y-%m-%d')}")
print(f"{'='*60}")

if FAILED > 0:
    print(f"\n  ⚠ {FAILED} test(s) FAILED!")
    sys.exit(1)
else:
    print(f"\n  ✓ ALL {TOTAL} TESTS PASSED")
    sys.exit(0)
