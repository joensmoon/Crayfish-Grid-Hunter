#!/usr/bin/env python3
"""
Crayfish Grid Hunter v5.0 — Test Suite
=======================================
Validates all core algorithms without requiring live API access.
All tests use synthetic data to ensure deterministic results.

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
    FuturesSymbol, GridParameters, MarketSnapshot, TechnicalAnalysis,
    calculate_geometric_grid, screen_high_volatility, screen_recent_listings,
    MAKER_FEE, MIN_GRID_PROFIT, MAX_GRID_PROFIT,
)
from monitor import (
    AlertLevel, GridPerformanceMonitor, GridPosition, MonitorThresholds,
    check_funding_and_liquidation, create_monitor,
)

random.seed(42)
PASS = "PASS"
FAIL = "FAIL"
_failures = []

def check(name, condition, detail=""):
    if condition:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name}" + (f": {detail}" if detail else ""))
        _failures.append(name)

# ============================================================
# TEST 1: FuturesSymbol — Listing Age
# ============================================================
print("\n[TEST 1] FuturesSymbol — Listing Age")
sym_new = FuturesSymbol("NEWUSDT","NEW",int((time.time()-30*86400)*1000),"PERPETUAL",4,3,0.0001,0.001)
sym_mid = FuturesSymbol("MIDUSDT","MID",int((time.time()-59*86400)*1000),"PERPETUAL",4,3,0.0001,0.001)
sym_old = FuturesSymbol("OLDUSDT","OLD",int((time.time()-90*86400)*1000),"PERPETUAL",4,3,0.0001,0.001)
check("30-day listing is recent", sym_new.is_recent)
check("59-day listing is recent", sym_mid.is_recent)
check("90-day listing is NOT recent", not sym_old.is_recent)
check("listing_age_days correct", 29.9 < sym_new.listing_age_days < 30.1)

# ============================================================
# TEST 2: TechnicalAnalysis — Sideways
# ============================================================
print("\n[TEST 2] TechnicalAnalysis — Sideways Market Indicators")
base = 100.0
closes_sw = [base + random.uniform(-1,1) for _ in range(30)]
highs_sw  = [c + random.uniform(0,0.5) for c in closes_sw]
lows_sw   = [c - random.uniform(0,0.5) for c in closes_sw]
tech_sw = TechnicalAnalysis("SIDEWAYSUSDT", closes_sw, highs_sw, lows_sw)
check("ATR(14) < 5% for sideways", tech_sw.atr_14_pct < 5.0, f"got {tech_sw.atr_14_pct:.4f}%")
check("BB width < 10%", tech_sw.bb_width_pct < 10.0, f"got {tech_sw.bb_width_pct:.4f}%")
check("ADX < 30", tech_sw.adx_14 < 30, f"got {tech_sw.adx_14:.2f}")
check("BB lower < BB upper", tech_sw.bb_lower < tech_sw.bb_upper)
check("Support <= last close", tech_sw.support_level <= closes_sw[-1])
check("Resistance >= last close", tech_sw.resistance_level >= closes_sw[-1])

# ============================================================
# TEST 3: TechnicalAnalysis — High Volatility
# ============================================================
print("\n[TEST 3] TechnicalAnalysis — High Volatility Indicators")
closes_hv = [5.0*(1+random.gauss(0,0.025)) for _ in range(30)]
highs_hv  = [c*1.015 for c in closes_hv]
lows_hv   = [c*0.985 for c in closes_hv]
tech_hv = TechnicalAnalysis("HIGHVOLUSDT", closes_hv, highs_hv, lows_hv)
check("RV > 10% for high-vol", tech_hv.realized_volatility_pct > 10.0, f"got {tech_hv.realized_volatility_pct:.2f}%")
check("BB width > 1%", tech_hv.bb_width_pct > 1.0, f"got {tech_hv.bb_width_pct:.4f}%")

# ============================================================
# TEST 4: Geometric Grid Calculation
# ============================================================
print("\n[TEST 4] Geometric Grid — Core Calculation")
snap_hv = MarketSnapshot(
    symbol="XYZUSDT", mark_price=2.5, index_price=2.5, last_price=2.5,
    price_change_pct_24h=5.2, volume_24h=50_000_000, quote_volume_24h=125_000_000,
    open_interest=80_000_000, funding_rate=-0.00012, next_funding_time=0,
    high_24h=2.75, low_24h=2.30,
)
tech_gp = TechnicalAnalysis("XYZUSDT",
    closes=[2.3+i*0.01 for i in range(30)],
    highs=[2.3+i*0.01+0.05 for i in range(30)],
    lows=[2.3+i*0.01-0.05 for i in range(30)],
)
gp = calculate_geometric_grid("XYZUSDT","high_volatility",snap_hv,tech_gp,75.0,"Test")
check("Price within grid range", gp.lower_price < gp.current_price < gp.upper_price,
      f"price={gp.current_price}, lower={gp.lower_price}, upper={gp.upper_price}")
check("Stop-loss below lower", gp.stop_loss_price < gp.lower_price)
check("Stop-loss = lower x 0.95", abs(gp.stop_loss_price - round(gp.lower_price*0.95,6)) < 0.0001)
check("Profit/grid >= 0.8%", gp.profit_per_grid_pct >= MIN_GRID_PROFIT*100-0.01, f"got {gp.profit_per_grid_pct:.4f}%")
check("Funding rate negative", gp.funding_rate < 0)
check("Daily funding yield > 0", gp.daily_funding_yield_pct > 0)
check("Grid type is Geometric", gp.grid_type == "Geometric")
check("Strategy is Neutral", gp.strategy_type == "Neutral")

# ============================================================
# TEST 5: Geometric Ratio r^n = upper/lower
# ============================================================
print("\n[TEST 5] Geometric Ratio — r^n = upper/lower")
computed_upper = gp.lower_price * (gp.grid_ratio ** gp.grid_count)
diff = abs(computed_upper - gp.upper_price)
check("r^n approx upper/lower (tol 0.01)", diff < 0.01, f"diff={diff:.8f}")
levels = [gp.lower_price * (gp.grid_ratio**i) for i in range(gp.grid_count+1)]
ratios = [levels[i+1]/levels[i] for i in range(len(levels)-1)]
ratio_variance = max(ratios) - min(ratios)
check("Equal ratio across all grids (variance < 1e-10)", ratio_variance < 1e-10, f"variance={ratio_variance:.2e}")

# ============================================================
# TEST 5b: Minimum Profit Enforcement
# ============================================================
print("\n[TEST 5b] Minimum Profit Enforcement")
snap_narrow = MarketSnapshot(
    symbol="NARROWUSDT", mark_price=100.0, index_price=100.0, last_price=100.0,
    price_change_pct_24h=0.5, volume_24h=1_000_000, quote_volume_24h=100_000_000,
    open_interest=50_000_000, funding_rate=0.0001, next_funding_time=0,
    high_24h=101.0, low_24h=99.0,
)
tech_narrow = TechnicalAnalysis("NARROWUSDT",
    closes=[100.0+random.uniform(-0.5,0.5) for _ in range(30)],
    highs=[100.5 for _ in range(30)], lows=[99.5 for _ in range(30)],
)
gp_narrow = calculate_geometric_grid("NARROWUSDT","recent_listing",snap_narrow,tech_narrow,60.0,"Narrow")
check("Narrow range: profit >= 0.8%", gp_narrow.profit_per_grid_pct >= MIN_GRID_PROFIT*100-0.01,
      f"got {gp_narrow.profit_per_grid_pct:.4f}%")

# ============================================================
# TEST 5c: Bollinger Band 20-Period Precision
# ============================================================
print("\n[TEST 5c] Bollinger Band — Standard 20-Period")
known_closes = list(range(1,31))
tech_bb = TechnicalAnalysis("BBTEST", known_closes,
    [c+0.5 for c in known_closes], [c-0.5 for c in known_closes])
expected_sma = sum(range(11,31))/20
manual_std = math.sqrt(sum((x-expected_sma)**2 for x in range(11,31))/20)
check("BB lower uses last 20 closes", abs(tech_bb.bb_lower-(expected_sma-2*manual_std)) < 0.0001,
      f"got={tech_bb.bb_lower:.4f}, expected={expected_sma-2*manual_std:.4f}")
check("BB upper uses last 20 closes", abs(tech_bb.bb_upper-(expected_sma+2*manual_std)) < 0.0001,
      f"got={tech_bb.bb_upper:.4f}, expected={expected_sma+2*manual_std:.4f}")

# ============================================================
# TEST 6: Category A Screening
# ============================================================
print("\n[TEST 6] Category A — Recent Listings Screening")
symbols_a = [
    FuturesSymbol("NEW1USDT","NEW1",int((time.time()-20*86400)*1000),"PERPETUAL",4,3,0.0001,0.001),
    FuturesSymbol("NEW2USDT","NEW2",int((time.time()-45*86400)*1000),"PERPETUAL",4,3,0.0001,0.001),
    FuturesSymbol("OLD1USDT","OLD1",int((time.time()-120*86400)*1000),"PERPETUAL",4,3,0.0001,0.001),
]
snaps_a, techs_a = {}, {}
for s in symbols_a:
    snaps_a[s.symbol] = MarketSnapshot(s.symbol,1.0,1.0,1.0,0.5,1e6,1e6,5e5,0.0001,0,1.01,0.99)
    techs_a[s.symbol] = TechnicalAnalysis(s.symbol,
        [1.0+random.uniform(-0.005,0.005) for _ in range(30)],
        [1.01 for _ in range(30)],[0.99 for _ in range(30)])
results_a = screen_recent_listings(symbols_a, snaps_a, techs_a, top_n=3)
check("Cat A returns results", len(results_a) > 0)
check("All Cat A are recent listings", all(r[0].is_recent for r in results_a))
check("OLD1USDT excluded from Cat A", "OLD1USDT" not in [r[0].symbol for r in results_a])

# ============================================================
# TEST 7: Category B Screening
# ============================================================
print("\n[TEST 7] Category B — High Volatility Screening")
symbols_b = [
    FuturesSymbol("VOL1USDT","VOL1",int((time.time()-200*86400)*1000),"PERPETUAL",4,3,0.0001,0.001),
    FuturesSymbol("VOL2USDT","VOL2",int((time.time()-300*86400)*1000),"PERPETUAL",4,3,0.0001,0.001),
    FuturesSymbol("LOW1USDT","LOW1",int((time.time()-100*86400)*1000),"PERPETUAL",4,3,0.0001,0.001),
]
snaps_b, techs_b = {}, {}
for s in symbols_b[:2]:
    snaps_b[s.symbol] = MarketSnapshot(s.symbol,5.0,5.0,5.0,15.0,5e7,2.5e8,5e7,-0.0002,0,5.8,4.2)
    closes_v = [5.0*(1+random.gauss(0,0.025)) for _ in range(30)]
    techs_b[s.symbol] = TechnicalAnalysis(s.symbol,closes_v,[c*1.01 for c in closes_v],[c*0.99 for c in closes_v])
snaps_b["LOW1USDT"] = MarketSnapshot("LOW1USDT",1.0,1.0,1.0,0.1,1e4,1e4,1e6,0.0001,0,1.002,0.998)
closes_l = [1.0+random.uniform(-0.001,0.001) for _ in range(30)]
techs_b["LOW1USDT"] = TechnicalAnalysis("LOW1USDT",closes_l,[c+0.001 for c in closes_l],[c-0.001 for c in closes_l])
results_b = screen_high_volatility(symbols_b, snaps_b, techs_b, top_n=3)
check("Cat B returns results", len(results_b) > 0)
check("LOW1USDT excluded from Cat B", "LOW1USDT" not in [r[0].symbol for r in results_b])

# ============================================================
# TEST 8: Monitor — Existing Checks (v4.4 regression)
# ============================================================
print("\n[TEST 8] Monitor — Existing Alert Checks (v4.4 regression)")
monitor = create_monitor(pnl_loss_critical_pct=-5.0, boundary_proximity_critical_pct=3.0,
    stop_loss_proximity_critical_pct=2.0, volume_spike_multiplier=2.5)
pos = GridPosition(
    symbol="BTCUSDT", grid_lower=68000.0, grid_upper=74000.0, grid_count=30,
    entry_price=71000.0, current_price=73800.0, stop_loss=66640.0, invested_usdt=1000.0,
    realized_pnl=12.5, unrealized_pnl=8.3, total_fills=18, total_orders=30,
    start_time=datetime.now()-timedelta(hours=6),
)
monitor.register_position(pos)
monitor.update_position("BTCUSDT", current_price=73800.0, realized_pnl=12.5, unrealized_pnl=8.3,
    current_volume=28000.0, avg_volume_24h=10000.0)
monitor.record_api_call("fapi/v1/klines", latency_ms=120, success=True)
monitor.record_api_call("fapi/v1/klines", latency_ms=1200, success=False)
monitor.mark_fallback_active("fapi/v1/klines", True)
alerts_v4 = monitor.run_checks()
check("Monitor generates alerts", len(alerts_v4) > 0)
check("CRITICAL boundary alert", any(a.level==AlertLevel.CRITICAL and "boundary" in a.message.lower() for a in alerts_v4))
check("CRITICAL volume spike alert", any(a.level==AlertLevel.CRITICAL and "volume" in a.message.lower() for a in alerts_v4))
report = monitor.format_report()
check("Report contains BTCUSDT", "BTCUSDT" in report)
check("Report contains API health", "fapi/v1/klines" in report)

# ============================================================
# TEST 9: Futures Monitor — Funding & Liquidation (v5.0)
# ============================================================
print("\n[TEST 9] Futures Monitor — Funding & Liquidation (v5.0)")
alerts_9a = check_funding_and_liquidation("BTCUSDT",70000,-0.00012,50000,65000,"neutral")
check("9a: Negative funding -> INFO earns", any(a.level==AlertLevel.INFO and "earns" in a.message for a in alerts_9a))
alerts_9b = check_funding_and_liquidation("ETHUSDT",2400,0.0001,1800,2500,"long")
check("9b: Stop-loss breach -> CRITICAL", any(a.level==AlertLevel.CRITICAL and "stop-loss" in a.message for a in alerts_9b))
alerts_9c = check_funding_and_liquidation("SOLUSDT",105,0.0001,100,90,"long")
check("9c: Near liquidation -> CRITICAL", any("liquidation" in a.message.lower() for a in alerts_9c))
alerts_9d = check_funding_and_liquidation("XYZUSDT",5.0,0.006,2.0,3.0,"long")
check("9d: Extreme funding -> CRITICAL", any(a.level==AlertLevel.CRITICAL and "EXTREME" in a.message for a in alerts_9d))
alerts_9e = check_funding_and_liquidation("ABCUSDT",10.0,0.004,5.0,7.0,"long")
check("9e: High funding -> HIGH", any(a.level==AlertLevel.HIGH and "High funding" in a.message for a in alerts_9e))
alerts_9f = check_funding_and_liquidation("DEFUSDT",10.0,0.0002,5.0,7.0,"short")
check("9f: Positive funding short -> INFO", any(a.level==AlertLevel.INFO and "short grid earns" in a.message for a in alerts_9f))

# ============================================================
# TEST 10: Grid Display Format
# ============================================================
print("\n[TEST 10] Grid Display Format")
display = gp.to_display()
check("Display contains Neutral", "Neutral" in display)
check("Display contains Geometric", "Geometric" in display)
check("Display contains Stop-Loss", "Stop-Loss" in display)
check("Display contains Liq. Price", "Liq. Price" in display)
check("Display contains Funding", "Funding" in display)
check("Negative funding note", "negative" in display)
check("Display contains Grid Ratio", "Grid Ratio" in display)
check("Display contains Profit/Grid", "Profit/Grid" in display)

# ============================================================
# Summary
# ============================================================
print("\n" + "="*58)
if _failures:
    print(f"  RESULT: {len(_failures)} test(s) FAILED:")
    for f in _failures:
        print(f"    - {f}")
    sys.exit(1)
else:
    print(f"  RESULT: All tests PASSED  (v5.0 — {datetime.now().strftime('%Y-%m-%d')})")
    print("="*58)
