"""
Deep Output Test — Crayfish Grid Hunter v2.0.0
===============================================
Simulates full Category A (次新币横盘) and Category B (高波动套利) output
using realistic synthetic data that mirrors real Binance Futures market conditions.
"""
import sys
import os
import time
import math
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills", "crayfish-grid-hunter"))

from grid_hunter_v5 import (
    FuturesSymbol, MarketSnapshot, TechnicalAnalysis, TokenMarketData,
    GridParameters, UserConfig, calculate_geometric_grid,
    screen_recent_contracts, screen_high_volatility, format_scan_output,
    MAKER_FEE, VERSION,
)

# ============================================================
# Synthetic Data Builder
# ============================================================

def make_symbol(symbol: str, base: str, age_days: float) -> FuturesSymbol:
    onboard_ms = int((time.time() - age_days * 86400) * 1000)
    return FuturesSymbol(
        symbol=symbol,
        base_asset=base,
        onboard_date=onboard_ms,
        contract_type="PERPETUAL",
        price_precision=4,
        qty_precision=3,
        tick_size=0.0001,
        step_size=0.001,
    )


def make_snap(symbol: str, price: float, vol_24h_pct: float,
              quote_vol: float, funding: float = 0.0001,
              oi: float = 5_000_000) -> MarketSnapshot:
    high = price * (1 + vol_24h_pct / 200)
    low  = price * (1 - vol_24h_pct / 200)
    return MarketSnapshot(
        symbol=symbol,
        mark_price=price,
        index_price=price * 0.9998,
        last_price=price,
        price_change_pct_24h=vol_24h_pct * 0.3,
        volume_24h=quote_vol / price,
        quote_volume_24h=quote_vol,
        open_interest=oi,
        funding_rate=funding,
        next_funding_time=int(time.time() * 1000) + 8 * 3600 * 1000,
        high_24h=high,
        low_24h=low,
    )


def make_tech_sideways(symbol: str, price: float, atr_pct: float = 1.2,
                       bb_width: float = 3.5, adx: float = 14.0,
                       vol_shrink: float = 0.30) -> TechnicalAnalysis:
    """Simulate sideways consolidation technical data."""
    import random
    random.seed(hash(symbol) % 9999)
    closes = []
    p = price * 0.97
    for i in range(30):
        p = p * (1 + random.uniform(-0.008, 0.008))
        closes.append(p)
    closes[-1] = price
    highs = [c * (1 + random.uniform(0.003, 0.012)) for c in closes]
    lows  = [c * (1 - random.uniform(0.003, 0.012)) for c in closes]
    vols  = [random.uniform(3e6, 8e6) for _ in closes]
    # Override last 7 days with lower volume (shrinkage)
    for i in range(-7, 0):
        vols[i] = vols[i] * vol_shrink
    tech = TechnicalAnalysis(symbol, closes, highs, lows, vols)
    # Manually override key indicators for test precision
    tech._atr_14_pct = atr_pct
    tech._bb_width_pct = bb_width
    tech._adx_14 = adx
    tech._volume_shrinkage_ratio = vol_shrink  # Use new override attribute
    return tech


def make_tech_volatile(symbol: str, price: float, atr_pct: float = 4.5,
                       bb_width: float = 12.0, adx: float = 28.0,
                       rv_pct: float = 85.0) -> TechnicalAnalysis:
    """Simulate high-volatility technical data."""
    import random
    random.seed(hash(symbol) % 9999 + 1)
    closes = []
    p = price * 0.85
    for i in range(30):
        p = p * (1 + random.uniform(-0.025, 0.028))
        closes.append(p)
    closes[-1] = price
    highs = [c * (1 + random.uniform(0.015, 0.045)) for c in closes]
    lows  = [c * (1 - random.uniform(0.015, 0.045)) for c in closes]
    vols  = [random.uniform(20e6, 80e6) for _ in closes]
    tech = TechnicalAnalysis(symbol, closes, highs, lows, vols)
    tech._atr_14_pct = atr_pct
    tech._bb_width_pct = bb_width
    tech._adx_14 = adx
    tech._rv_pct = rv_pct
    return tech


def make_token_data(base: str, mcap: float) -> TokenMarketData:
    return TokenMarketData(
        symbol=base,
        market_cap=mcap,
        volume_24h_usd=mcap * 0.8,  # simulate 80% turnover
    )


# ============================================================
# Patch TechnicalAnalysis to support manual override
# ============================================================

_orig_atr = TechnicalAnalysis.atr_14_pct.fget
_orig_bb  = TechnicalAnalysis.bb_width_pct.fget
_orig_adx = TechnicalAnalysis.adx_14.fget

def _patched_atr(self):
    return getattr(self, '_atr_14_pct', _orig_atr(self))

def _patched_bb(self):
    return getattr(self, '_bb_width_pct', _orig_bb(self))

def _patched_adx(self):
    return getattr(self, '_adx_14', _orig_adx(self))

TechnicalAnalysis.atr_14_pct = property(_patched_atr)
TechnicalAnalysis.bb_width_pct = property(_patched_bb)
TechnicalAnalysis.adx_14 = property(_patched_adx)

# Also patch realized_volatility_pct
_orig_rv = TechnicalAnalysis.realized_volatility_pct.fget
def _patched_rv(self):
    return getattr(self, '_rv_pct', _orig_rv(self))
TechnicalAnalysis.realized_volatility_pct = property(_patched_rv)


# ============================================================
# Build Test Datasets
# ============================================================

# --- Category A: 次新币横盘类 ---
# 3 recent contracts in sideways consolidation
cat_a_symbols = [
    make_symbol("NEWCOINUSDT",  "NEWCOIN",  45.0),   # 45 days old
    make_symbol("FRESHUSDT",    "FRESH",    62.0),   # 62 days old
    make_symbol("RECENTUSDT",   "RECENT",   78.0),   # 78 days old
    make_symbol("OLDCOINUSDT",  "OLDCOIN", 150.0),   # 150 days — should be filtered out
    make_symbol("TRENDINGUSDT", "TRENDING", 30.0),   # 30 days but trending (high ADX)
]

cat_a_snaps = {
    "NEWCOINUSDT":  make_snap("NEWCOINUSDT",  0.4523, 3.2,  45_000_000, funding=0.0001),
    "FRESHUSDT":    make_snap("FRESHUSDT",    1.2340, 2.8,  28_000_000, funding=-0.0002),
    "RECENTUSDT":   make_snap("RECENTUSDT",   0.0892, 4.1,  18_000_000, funding=0.0003),
    "OLDCOINUSDT":  make_snap("OLDCOINUSDT",  2.3400, 5.5,  55_000_000, funding=0.0001),
    "TRENDINGUSDT": make_snap("TRENDINGUSDT", 0.7800, 8.5,  32_000_000, funding=0.0002),
}

cat_a_techs = {
    "NEWCOINUSDT":  make_tech_sideways("NEWCOINUSDT",  0.4523, atr_pct=1.1, bb_width=3.2, adx=12.5, vol_shrink=0.28),
    "FRESHUSDT":    make_tech_sideways("FRESHUSDT",    1.2340, atr_pct=1.5, bb_width=4.1, adx=16.8, vol_shrink=0.35),
    "RECENTUSDT":   make_tech_sideways("RECENTUSDT",   0.0892, atr_pct=1.8, bb_width=4.8, adx=18.5, vol_shrink=0.40),
    "OLDCOINUSDT":  make_tech_sideways("OLDCOINUSDT",  2.3400, atr_pct=2.5, bb_width=6.2, adx=25.0, vol_shrink=0.45),
    "TRENDINGUSDT": make_tech_sideways("TRENDINGUSDT", 0.7800, atr_pct=1.3, bb_width=3.8, adx=32.0, vol_shrink=0.25),
}

# --- Category B: 高波动套利类 ---
# 3 high-volatility candidates with proper market cap
cat_b_symbols = [
    make_symbol("HOTCOINUSDT",  "HOTCOIN",  200.0),   # established
    make_symbol("VOLATILUSDT",  "VOLATIL",  180.0),
    make_symbol("ARBITUSDT",    "ARBIT",    250.0),
    make_symbol("BIGCAPUSDT",   "BIGCAP",   300.0),   # market cap too large
    make_symbol("SMALLCAPUSDT", "SMALLCAP", 120.0),   # market cap too small
]

cat_b_snaps = {
    "HOTCOINUSDT":  make_snap("HOTCOINUSDT",  3.4560, 18.5, 380_000_000, funding=-0.0005, oi=15_000_000),
    "VOLATILUSDT":  make_snap("VOLATILUSDT",  0.2345, 22.3, 290_000_000, funding=0.0003,  oi=8_000_000),
    "ARBITUSDT":    make_snap("ARBITUSDT",    12.340, 15.8, 210_000_000, funding=-0.0002, oi=12_000_000),
    "BIGCAPUSDT":   make_snap("BIGCAPUSDT",   45.670, 12.0, 500_000_000, funding=0.0001,  oi=20_000_000),
    "SMALLCAPUSDT": make_snap("SMALLCAPUSDT", 0.0123, 25.0,  15_000_000, funding=0.0002,  oi=2_000_000),
}

cat_b_techs = {
    "HOTCOINUSDT":  make_tech_volatile("HOTCOINUSDT",  3.4560, atr_pct=4.8, bb_width=13.5, adx=30.2, rv_pct=92.0),
    "VOLATILUSDT":  make_tech_volatile("VOLATILUSDT",  0.2345, atr_pct=5.2, bb_width=15.8, adx=27.5, rv_pct=108.0),
    "ARBITUSDT":    make_tech_volatile("ARBITUSDT",    12.340, atr_pct=3.9, bb_width=11.2, adx=25.8, rv_pct=78.0),
    "BIGCAPUSDT":   make_tech_volatile("BIGCAPUSDT",   45.670, atr_pct=3.2, bb_width=9.5,  adx=22.0, rv_pct=62.0),
    "SMALLCAPUSDT": make_tech_volatile("SMALLCAPUSDT", 0.0123, atr_pct=6.5, bb_width=18.0, adx=35.0, rv_pct=125.0),
}

cat_b_token_data = {
    "HOTCOIN":  make_token_data("HOTCOIN",  450_000_000),   # $450M — in range
    "VOLATIL":  make_token_data("VOLATIL",  320_000_000),   # $320M — in range
    "ARBIT":    make_token_data("ARBIT",    680_000_000),   # $680M — in range
    "BIGCAP":   make_token_data("BIGCAP",  2_500_000_000),  # $2.5B — too large
    "SMALLCAP": make_token_data("SMALLCAP",  80_000_000),   # $80M — too small
}

# All symbols combined for full test
all_symbols = cat_a_symbols + cat_b_symbols
all_snaps = {**cat_a_snaps, **cat_b_snaps}
all_techs = {**cat_a_techs, **cat_b_techs}


# ============================================================
# Run Screening
# ============================================================

print("\n" + "="*70)
print("  DEEP OUTPUT TEST — Crayfish Grid Hunter v2.0.0")
print("  Testing Category A (次新币横盘) + Category B (高波动套利)")
print("="*70)

config = UserConfig()

# Screen Category A
cat_a_raw = screen_recent_contracts(
    all_symbols, all_snaps, all_techs, top_n=3, config=config
)

# Screen Category B
cat_b_raw = screen_high_volatility(
    all_symbols, all_snaps, all_techs, cat_b_token_data, top_n=3, config=config
)

# Build GridParameters
cat_a_results = []
for sym, snap, tech, score, reason in cat_a_raw:
    gp = calculate_geometric_grid(
        sym.symbol, "recent_contract", snap, tech, score, reason,
        leverage=config.leverage
    )
    cat_a_results.append(gp)

cat_b_results = []
for sym, snap, tech, score, reason in cat_b_raw:
    tdata = cat_b_token_data.get(sym.base_asset)
    mcap = tdata.market_cap if tdata else 0
    turnover = snap.quote_volume_24h / mcap if mcap > 0 else 0
    gp = calculate_geometric_grid(
        sym.symbol, "high_volatility", snap, tech, score, reason,
        market_cap=mcap, turnover_rate=turnover,
        leverage=config.leverage,
    )
    cat_b_results.append(gp)

# ============================================================
# Print Full Output
# ============================================================

output = format_scan_output(cat_a_results, cat_b_results, config=config)
print(output)

# ============================================================
# Print Individual Grid Details
# ============================================================

print("\n" + "="*70)
print("  INDIVIDUAL GRID DETAILS — Category A (次新币横盘类)")
print("="*70)
for gp in cat_a_results:
    print(gp.to_display())

print("\n" + "="*70)
print("  INDIVIDUAL GRID DETAILS — Category B (高波动套利类)")
print("="*70)
for gp in cat_b_results:
    print(gp.to_display())

# ============================================================
# Screening Filter Verification
# ============================================================

print("\n" + "="*70)
print("  FILTER VERIFICATION")
print("="*70)

print(f"\n  Category A — Screening Results:")
print(f"  Total candidates tested: {len(cat_a_symbols)}")
print(f"  Passed filters: {len(cat_a_results)}")
for sym, snap, tech, score, reason in cat_a_raw:
    print(f"  ✓ {sym.symbol} (age={sym.contract_age_days:.0f}d, score={score:.1f}): {reason}")

filtered_out_a = [s for s in cat_a_symbols if s.symbol not in {r[0].symbol for r in cat_a_raw}]
for sym in filtered_out_a:
    tech = all_techs.get(sym.symbol)
    snap = all_snaps.get(sym.symbol)
    age = sym.contract_age_days
    reasons = []
    if age > config.contract_recent_days:
        reasons.append(f"age={age:.0f}d > {config.contract_recent_days}d")
    if tech and tech.adx_14 >= config.adx_sideways:
        reasons.append(f"ADX={tech.adx_14:.1f} >= {config.adx_sideways}")
    print(f"  ✗ {sym.symbol}: filtered ({', '.join(reasons) if reasons else 'did not pass all criteria'})")

print(f"\n  Category B — Screening Results:")
print(f"  Total candidates tested: {len(cat_b_symbols)}")
print(f"  Passed filters: {len(cat_b_results)}")
for sym, snap, tech, score, reason in cat_b_raw:
    tdata = cat_b_token_data.get(sym.base_asset)
    mcap = tdata.market_cap if tdata else 0
    print(f"  ✓ {sym.symbol} (mcap=${mcap/1e6:.0f}M, score={score:.1f}): {reason}")

filtered_out_b = [s for s in cat_b_symbols if s.symbol not in {r[0].symbol for r in cat_b_raw}]
for sym in filtered_out_b:
    tdata = cat_b_token_data.get(sym.base_asset)
    mcap = tdata.market_cap if tdata else 0
    snap = all_snaps.get(sym.symbol)
    reasons = []
    if mcap < config.mcap_min:
        reasons.append(f"mcap=${mcap/1e6:.0f}M < ${config.mcap_min/1e6:.0f}M")
    elif mcap > config.mcap_max:
        reasons.append(f"mcap=${mcap/1e6:.0f}M > ${config.mcap_max/1e6:.0f}M")
    if snap and mcap > 0:
        turnover = snap.quote_volume_24h / mcap
        if turnover < config.turnover_min:
            reasons.append(f"turnover={turnover*100:.0f}% < {config.turnover_min*100:.0f}%")
    print(f"  ✗ {sym.symbol}: filtered ({', '.join(reasons) if reasons else 'did not pass all criteria'})")

# ============================================================
# Geometric Grid Precision Check
# ============================================================

print("\n" + "="*70)
print("  GEOMETRIC GRID PRECISION CHECK")
print("="*70)

issues = []
for gp in cat_a_results + cat_b_results:
    if gp.grid_count < 10:
        issues.append(f"  [WARN] {gp.symbol}: grid_count={gp.grid_count} < 10 (too few grids)")
    if gp.profit_per_grid_pct < 0.8:
        issues.append(f"  [WARN] {gp.symbol}: profit_per_grid={gp.profit_per_grid_pct:.3f}% < 0.8% (below minimum)")
    if gp.profit_per_grid_pct > 3.0:
        issues.append(f"  [WARN] {gp.symbol}: profit_per_grid={gp.profit_per_grid_pct:.3f}% > 3.0% (too wide grids)")
    if gp.stop_loss_price >= gp.lower_price:
        issues.append(f"  [FAIL] {gp.symbol}: stop_loss={gp.stop_loss_price:.4f} >= lower={gp.lower_price:.4f}")
    if gp.liquidation_price >= gp.lower_price:
        issues.append(f"  [WARN] {gp.symbol}: liquidation={gp.liquidation_price:.4f} >= lower={gp.lower_price:.4f}")
    # Verify geometric ratio
    expected_ratio = (gp.upper_price / gp.lower_price) ** (1 / gp.grid_count)
    ratio_error = abs(expected_ratio - gp.grid_ratio) / expected_ratio
    if ratio_error > 1e-5:
        issues.append(f"  [FAIL] {gp.symbol}: grid_ratio error={ratio_error:.2e}")
    else:
        print(f"  ✓ {gp.symbol}: r={gp.grid_ratio:.6f}, profit={gp.profit_per_grid_pct:.3f}%, grids={gp.grid_count}, stop=${gp.stop_loss_price:.4f}")

if issues:
    print("\n  Issues found:")
    for issue in issues:
        print(issue)
else:
    print("\n  All geometric grid calculations verified ✓")

print("\n" + "="*70)
print(f"  Deep output test complete. v{VERSION}")
print("="*70 + "\n")
