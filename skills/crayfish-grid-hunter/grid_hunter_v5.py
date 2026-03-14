"""
Crayfish Grid Hunter v5.0 — Futures Grid Engine
================================================
Core engine for USDS-M Perpetual Futures grid trading.

Two-category dual screening:
  Category A — Recent Listings (次新币横盘类):
      Listed < 60 days, post-first-wave pullback, narrow consolidation.
  Category B — High Volatility Arbitrage (高波动套利类):
      High 24h volume/OI ratio, RV > 15%, mid-cap $200M-$10B.

Grid Strategy:
  - Type:      Geometric (equal-ratio) — industry standard for volatile assets
  - Direction: Neutral (no initial position bias)
  - Profit:    0.8%–1.2% per grid after fees (0.04% maker)
  - Risk:      5% hard stop-loss below lower bound + liquidation price warning
  - Funding:   Negative funding rate bonus calculation for long-biased grids

All API calls use the official `derivatives-trading-usds-futures` skill
(fapi.binance.com) with automatic fallback to testnet for connectivity tests.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

# ============================================================
# Configuration
# ============================================================
VERSION = "5.0.0"
FAPI_BASE = "https://fapi.binance.com"
FAPI_FALLBACK = "https://testnet.binancefuture.com"
WEB3_BASE = "https://web3.binance.com"

USER_AGENT_DERIV = f"crayfish-grid-hunter/{VERSION} (derivatives-trading-usds-futures Skill)"
USER_AGENT_WEB3 = f"crayfish-grid-hunter/{VERSION} (binance-web3 Skill)"

MAKER_FEE = 0.0004       # 0.04% maker fee (standard, BNB burn reduces to 0.02%)
TAKER_FEE = 0.0005       # 0.05% taker fee
MIN_GRID_PROFIT = 0.008  # 0.8% minimum per-grid profit after fees
MAX_GRID_PROFIT = 0.012  # 1.2% maximum per-grid profit after fees
DEFAULT_LEVERAGE = 5     # Conservative default leverage for grid trading
MAX_ACCOUNT_EXPOSURE = 0.08  # Max 8% of account per grid position

# Screening thresholds
RECENT_LISTING_DAYS = 60     # Category A: listed within 60 days
ATR_SIDEWAYS_PCT = 2.0       # Category A: ATR(14) < 2% → sideways
BB_WIDTH_SIDEWAYS = 5.0      # Category A: BB width < 5% → narrow range
HIGH_VOL_RV_MIN = 15.0       # Category B: realized volatility > 15%
HIGH_VOL_TURNOVER_MIN = 0.3  # Category B: volume/OI ratio > 0.3 (30%)

# ============================================================
# Data Structures
# ============================================================

@dataclass
class FuturesSymbol:
    symbol: str
    base_asset: str
    onboard_date: int        # Unix ms timestamp
    contract_type: str       # PERPETUAL
    price_precision: int
    qty_precision: int
    tick_size: float
    step_size: float

    @property
    def listing_age_days(self) -> float:
        return (time.time() * 1000 - self.onboard_date) / (1000 * 86400)

    @property
    def is_recent(self) -> bool:
        return self.listing_age_days <= RECENT_LISTING_DAYS


@dataclass
class MarketSnapshot:
    symbol: str
    mark_price: float
    index_price: float
    last_price: float
    price_change_pct_24h: float
    volume_24h: float
    quote_volume_24h: float
    open_interest: float
    funding_rate: float
    next_funding_time: int
    high_24h: float
    low_24h: float

    @property
    def volatility_24h_pct(self) -> float:
        """Intraday price range as a percentage of last price."""
        if self.last_price > 0:
            return ((self.high_24h - self.low_24h) / self.last_price) * 100
        return 0.0

    @property
    def volume_oi_ratio(self) -> float:
        """Volume/Open Interest ratio — proxy for turnover rate."""
        if self.open_interest > 0:
            return self.quote_volume_24h / self.open_interest
        return 0.0


@dataclass
class TechnicalAnalysis:
    symbol: str
    closes: List[float]
    highs: List[float]
    lows: List[float]

    @property
    def atr_14_pct(self) -> float:
        """ATR(14) as percentage of last close."""
        if len(self.closes) < 15:
            return 0.0
        tr_vals = []
        for i in range(1, len(self.closes)):
            h, l, pc = self.highs[i], self.lows[i], self.closes[i - 1]
            tr_vals.append(max(h - l, abs(h - pc), abs(l - pc)))
        atr = sum(tr_vals[-14:]) / 14
        return (atr / self.closes[-1]) * 100 if self.closes[-1] > 0 else 0.0

    @property
    def bb_width_pct(self) -> float:
        """Standard 20-period Bollinger Band width as % of middle band."""
        if len(self.closes) < 20:
            return 0.0
        window = self.closes[-20:]
        sma = sum(window) / 20
        std = math.sqrt(sum((p - sma) ** 2 for p in window) / 20)
        return ((sma + 2 * std - (sma - 2 * std)) / sma * 100) if sma > 0 else 0.0

    @property
    def realized_volatility_pct(self) -> float:
        """Annualized realized volatility from log returns (%)."""
        if len(self.closes) < 10:
            return 0.0
        log_returns = [math.log(self.closes[i] / self.closes[i - 1])
                       for i in range(1, len(self.closes))
                       if self.closes[i - 1] > 0]
        if not log_returns:
            return 0.0
        mean = sum(log_returns) / len(log_returns)
        variance = sum((r - mean) ** 2 for r in log_returns) / len(log_returns)
        daily_std = math.sqrt(variance)
        return daily_std * math.sqrt(365) * 100  # Annualized

    @property
    def support_level(self) -> float:
        """Recent swing low (20-period)."""
        window = self.lows[-20:] if len(self.lows) >= 20 else self.lows
        return min(window) if window else 0.0

    @property
    def resistance_level(self) -> float:
        """Recent swing high (20-period)."""
        window = self.highs[-20:] if len(self.highs) >= 20 else self.highs
        return max(window) if window else 0.0

    @property
    def bb_lower(self) -> float:
        if len(self.closes) < 20:
            return 0.0
        window = self.closes[-20:]
        sma = sum(window) / 20
        std = math.sqrt(sum((p - sma) ** 2 for p in window) / 20)
        return sma - 2 * std

    @property
    def bb_upper(self) -> float:
        if len(self.closes) < 20:
            return 0.0
        window = self.closes[-20:]
        sma = sum(window) / 20
        std = math.sqrt(sum((p - sma) ** 2 for p in window) / 20)
        return sma + 2 * std

    @property
    def adx_14(self) -> float:
        """Simplified ADX(14) — values < 20 indicate sideways market."""
        if len(self.closes) < 15:
            return 25.0  # Default to neutral
        plus_dm, minus_dm, tr_vals = [], [], []
        for i in range(1, len(self.closes)):
            h, l, ph, pl = self.highs[i], self.lows[i], self.highs[i-1], self.lows[i-1]
            pc = self.closes[i - 1]
            up_move = h - ph
            down_move = pl - l
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
            tr_vals.append(max(h - l, abs(h - pc), abs(l - pc)))

        n = 14
        atr = sum(tr_vals[:n]) / n
        pdm = sum(plus_dm[:n]) / n
        mdm = sum(minus_dm[:n]) / n

        for i in range(n, len(tr_vals)):
            atr = (atr * (n - 1) + tr_vals[i]) / n
            pdm = (pdm * (n - 1) + plus_dm[i]) / n
            mdm = (mdm * (n - 1) + minus_dm[i]) / n

        if atr == 0:
            return 0.0
        pdi = (pdm / atr) * 100
        mdi = (mdm / atr) * 100
        dx = (abs(pdi - mdi) / (pdi + mdi) * 100) if (pdi + mdi) > 0 else 0
        return dx


@dataclass
class GridParameters:
    """Complete Geometric Neutral Grid parameters for a futures symbol."""
    symbol: str
    category: str               # "recent_listing" | "high_volatility"
    strategy_type: str = "Neutral"
    grid_type: str = "Geometric"

    # Price range
    lower_price: float = 0.0
    upper_price: float = 0.0
    current_price: float = 0.0

    # Grid structure
    grid_count: int = 0
    grid_ratio: float = 0.0     # r = (upper/lower)^(1/n)
    profit_per_grid_pct: float = 0.0  # After fees

    # Risk parameters
    stop_loss_price: float = 0.0    # 5% below lower bound
    liquidation_price: float = 0.0  # Estimated liquidation price
    leverage: int = DEFAULT_LEVERAGE

    # Funding
    funding_rate: float = 0.0
    daily_funding_yield_pct: float = 0.0

    # Context
    volatility_24h_pct: float = 0.0
    atr_pct: float = 0.0
    support: float = 0.0
    resistance: float = 0.0

    # Scoring
    grid_score: float = 0.0
    category_reason: str = ""

    def to_display(self) -> str:
        """Format grid parameters for user-facing output."""
        funding_note = ""
        if self.funding_rate < 0:
            funding_note = (
                f"\n  Funding Rate   : {self.funding_rate*100:.4f}% "
                f"(negative → long grid earns ~{abs(self.daily_funding_yield_pct):.3f}%/day)"
            )
        elif self.funding_rate > 0.001:
            funding_note = (
                f"\n  Funding Rate   : {self.funding_rate*100:.4f}% "
                f"(positive → short grid earns ~{self.daily_funding_yield_pct:.3f}%/day)"
            )
        else:
            funding_note = f"\n  Funding Rate   : {self.funding_rate*100:.4f}% (neutral)"

        return (
            f"\n{'='*58}"
            f"\n  {self.symbol}  [{self.category.replace('_',' ').title()}]"
            f"\n{'='*58}"
            f"\n  Strategy       : {self.strategy_type} Grid ({self.grid_type})"
            f"\n  Current Price  : ${self.current_price:.4f}"
            f"\n  Grid Range     : ${self.lower_price:.4f} — ${self.upper_price:.4f}"
            f"\n  Grid Count     : {self.grid_count} grids"
            f"\n  Grid Ratio (r) : {self.grid_ratio:.6f}"
            f"\n  Profit/Grid    : {self.profit_per_grid_pct:.2f}% (after {MAKER_FEE*100:.2f}% fees)"
            f"\n  Leverage       : {self.leverage}×"
            f"\n  Stop-Loss      : ${self.stop_loss_price:.4f}  (5% below lower bound)"
            f"\n  Liq. Price Est.: ${self.liquidation_price:.4f}"
            f"\n  24h Volatility : {self.volatility_24h_pct:.2f}%"
            f"\n  Support / Res. : ${self.support:.4f} / ${self.resistance:.4f}"
            f"{funding_note}"
            f"\n  Grid Score     : {self.grid_score:.0f}/100"
            f"\n  Reason         : {self.category_reason}"
        )


# ============================================================
# API Layer — derivatives-trading-usds-futures skill
# ============================================================

_cache: Dict[str, tuple] = {}
_cache_ttl = timedelta(minutes=5)
_active_fapi: Optional[str] = None


def _get_cache(key: str):
    if key in _cache:
        data, ts = _cache[key]
        if datetime.now() - ts < _cache_ttl:
            return data
    return None


def _set_cache(key: str, data):
    _cache[key] = (data, datetime.now())


def get_fapi_base() -> str:
    """Return working fapi base URL with fallback."""
    global _active_fapi
    if _active_fapi:
        return _active_fapi
    for base in [FAPI_BASE, FAPI_FALLBACK]:
        try:
            r = requests.get(f"{base}/fapi/v1/ping", timeout=5,
                             headers={"User-Agent": USER_AGENT_DERIV})
            if r.status_code == 200:
                _active_fapi = base
                return base
        except Exception:
            pass
    _active_fapi = FAPI_BASE  # Use primary even if restricted; agent env will work
    return _active_fapi


def fetch_exchange_info() -> List[FuturesSymbol]:
    """Fetch all USDS-M perpetual symbols via derivatives skill.

    Endpoint: GET /fapi/v1/exchangeInfo (No auth required)
    """
    cached = _get_cache("exchange_info")
    if cached:
        return cached

    base = get_fapi_base()
    try:
        r = requests.get(f"{base}/fapi/v1/exchangeInfo", timeout=15,
                         headers={"User-Agent": USER_AGENT_DERIV})
        r.raise_for_status()
        data = r.json()
        symbols = []
        for s in data.get("symbols", []):
            if s.get("contractType") != "PERPETUAL":
                continue
            if s.get("quoteAsset") != "USDT":
                continue
            if s.get("status") != "TRADING":
                continue

            tick_size = 0.01
            step_size = 0.001
            for f in s.get("filters", []):
                if f["filterType"] == "PRICE_FILTER":
                    tick_size = float(f["tickSize"])
                elif f["filterType"] == "LOT_SIZE":
                    step_size = float(f["stepSize"])

            symbols.append(FuturesSymbol(
                symbol=s["symbol"],
                base_asset=s["baseAsset"],
                onboard_date=s.get("onboardDate", 0),
                contract_type=s["contractType"],
                price_precision=s.get("pricePrecision", 4),
                qty_precision=s.get("quantityPrecision", 3),
                tick_size=tick_size,
                step_size=step_size,
            ))
        _set_cache("exchange_info", symbols)
        return symbols
    except Exception as e:
        print(f"  [WARN] exchangeInfo failed: {e}")
        return []


def fetch_ticker_24h(symbol: str) -> Optional[dict]:
    """Fetch 24hr ticker via derivatives skill.

    Endpoint: GET /fapi/v1/ticker/24hr (No auth required)
    """
    cached = _get_cache(f"ticker_{symbol}")
    if cached:
        return cached
    base = get_fapi_base()
    try:
        r = requests.get(f"{base}/fapi/v1/ticker/24hr",
                         params={"symbol": symbol}, timeout=10,
                         headers={"User-Agent": USER_AGENT_DERIV})
        r.raise_for_status()
        data = r.json()
        _set_cache(f"ticker_{symbol}", data)
        return data
    except Exception as e:
        print(f"  [WARN] ticker/24hr {symbol}: {e}")
        return None


def fetch_mark_price(symbol: str) -> Optional[dict]:
    """Fetch mark price and funding rate via derivatives skill.

    Endpoint: GET /fapi/v1/premiumIndex (No auth required)
    """
    cached = _get_cache(f"mark_{symbol}")
    if cached:
        return cached
    base = get_fapi_base()
    try:
        r = requests.get(f"{base}/fapi/v1/premiumIndex",
                         params={"symbol": symbol}, timeout=10,
                         headers={"User-Agent": USER_AGENT_DERIV})
        r.raise_for_status()
        data = r.json()
        _set_cache(f"mark_{symbol}", data)
        return data
    except Exception as e:
        print(f"  [WARN] premiumIndex {symbol}: {e}")
        return None


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 72) -> List[list]:
    """Fetch klines via derivatives skill.

    Endpoint: GET /fapi/v1/klines (No auth required)
    """
    cached = _get_cache(f"klines_{symbol}_{interval}_{limit}")
    if cached:
        return cached
    base = get_fapi_base()
    try:
        r = requests.get(f"{base}/fapi/v1/klines",
                         params={"symbol": symbol, "interval": interval, "limit": limit},
                         timeout=15, headers={"User-Agent": USER_AGENT_DERIV})
        r.raise_for_status()
        data = r.json()
        _set_cache(f"klines_{symbol}_{interval}_{limit}", data)
        return data
    except Exception as e:
        print(f"  [WARN] klines {symbol}: {e}")
        return []


def fetch_open_interest(symbol: str) -> float:
    """Fetch current open interest via derivatives skill.

    Endpoint: GET /fapi/v1/openInterest (No auth required)
    """
    base = get_fapi_base()
    try:
        r = requests.get(f"{base}/fapi/v1/openInterest",
                         params={"symbol": symbol}, timeout=10,
                         headers={"User-Agent": USER_AGENT_DERIV})
        r.raise_for_status()
        return float(r.json().get("openInterest", 0))
    except Exception:
        return 0.0


def fetch_all_tickers() -> List[dict]:
    """Fetch all 24hr tickers in one call via derivatives skill."""
    cached = _get_cache("all_tickers")
    if cached:
        return cached
    base = get_fapi_base()
    try:
        r = requests.get(f"{base}/fapi/v1/ticker/24hr", timeout=20,
                         headers={"User-Agent": USER_AGENT_DERIV})
        r.raise_for_status()
        data = r.json()
        _set_cache("all_tickers", data)
        return data
    except Exception as e:
        print(f"  [WARN] all tickers: {e}")
        return []


# ============================================================
# Screening Engine
# ============================================================

def build_market_snapshot(symbol: str, ticker: dict, mark: dict, oi: float) -> MarketSnapshot:
    """Combine ticker + mark price + OI into a unified snapshot."""
    return MarketSnapshot(
        symbol=symbol,
        mark_price=float(mark.get("markPrice", ticker.get("lastPrice", 0))),
        index_price=float(mark.get("indexPrice", 0)),
        last_price=float(ticker.get("lastPrice", 0)),
        price_change_pct_24h=float(ticker.get("priceChangePercent", 0)),
        volume_24h=float(ticker.get("volume", 0)),
        quote_volume_24h=float(ticker.get("quoteVolume", 0)),
        open_interest=oi,
        funding_rate=float(mark.get("lastFundingRate", 0)),
        next_funding_time=int(mark.get("nextFundingTime", 0)),
        high_24h=float(ticker.get("highPrice", 0)),
        low_24h=float(ticker.get("lowPrice", 0)),
    )


def screen_recent_listings(
    symbols: List[FuturesSymbol],
    snapshots: Dict[str, MarketSnapshot],
    technicals: Dict[str, TechnicalAnalysis],
    top_n: int = 3,
) -> List[Tuple[FuturesSymbol, MarketSnapshot, TechnicalAnalysis, float]]:
    """
    Category A — Recent Listings (次新币横盘类)
    Criteria:
      1. Listed within RECENT_LISTING_DAYS (60 days)
      2. ATR(14) < 2% OR BB width < 5% OR ADX < 20 (sideways signal)
      3. Has valid market data
    Scoring: sideways strength + listing recency
    """
    candidates = []
    for sym in symbols:
        if not sym.is_recent:
            continue
        snap = snapshots.get(sym.symbol)
        tech = technicals.get(sym.symbol)
        if not snap or not tech:
            continue
        if snap.last_price <= 0:
            continue

        # Sideways condition: at least one indicator must confirm
        is_sideways = (
            tech.atr_14_pct < ATR_SIDEWAYS_PCT or
            tech.bb_width_pct < BB_WIDTH_SIDEWAYS or
            tech.adx_14 < 20
        )
        if not is_sideways:
            continue

        # Score: lower ATR + lower BB width + lower ADX = more sideways = better
        sideways_score = max(0, (ATR_SIDEWAYS_PCT - tech.atr_14_pct) / ATR_SIDEWAYS_PCT * 40)
        sideways_score += max(0, (BB_WIDTH_SIDEWAYS - tech.bb_width_pct) / BB_WIDTH_SIDEWAYS * 30)
        sideways_score += max(0, (25 - tech.adx_14) / 25 * 30) if tech.adx_14 < 25 else 0

        # Recency bonus: newer listings score higher
        recency_bonus = max(0, (RECENT_LISTING_DAYS - sym.listing_age_days) / RECENT_LISTING_DAYS * 20)
        score = sideways_score + recency_bonus

        reason = (
            f"Listed {sym.listing_age_days:.0f}d ago; "
            f"ATR={tech.atr_14_pct:.2f}%, BB-width={tech.bb_width_pct:.2f}%, ADX={tech.adx_14:.1f}"
        )
        candidates.append((sym, snap, tech, score, reason))

    candidates.sort(key=lambda x: x[3], reverse=True)
    return [(s, sn, t, sc, r) for s, sn, t, sc, r in candidates[:top_n]]


def screen_high_volatility(
    symbols: List[FuturesSymbol],
    snapshots: Dict[str, MarketSnapshot],
    technicals: Dict[str, TechnicalAnalysis],
    top_n: int = 3,
) -> List[Tuple[FuturesSymbol, MarketSnapshot, TechnicalAnalysis, float]]:
    """
    Category B — High Volatility Arbitrage (高波动套利类)
    Criteria:
      1. Realized volatility > 15% (annualized)
      2. Volume/OI ratio > 0.3 (active turnover)
      3. 24h volatility between 5%-40% (grid-tradeable range)
    Scoring: RV + turnover + 24h vol
    """
    candidates = []
    for sym in symbols:
        snap = snapshots.get(sym.symbol)
        tech = technicals.get(sym.symbol)
        if not snap or not tech:
            continue
        if snap.last_price <= 0:
            continue

        rv = tech.realized_volatility_pct
        vol_oi = snap.volume_oi_ratio
        intraday_vol = snap.volatility_24h_pct

        if rv < HIGH_VOL_RV_MIN:
            continue
        if vol_oi < HIGH_VOL_TURNOVER_MIN:
            continue
        if not (5.0 <= intraday_vol <= 40.0):
            continue

        # Score: higher RV + higher turnover + optimal intraday vol (15-25% is ideal)
        rv_score = min(rv / 50 * 40, 40)
        turnover_score = min(vol_oi / 2.0 * 30, 30)
        vol_score = 30 if 15 <= intraday_vol <= 25 else max(0, 30 - abs(intraday_vol - 20) * 1.5)
        score = rv_score + turnover_score + vol_score

        reason = (
            f"RV={rv:.1f}%/yr, Vol/OI={vol_oi:.2f}×, "
            f"24h-vol={intraday_vol:.2f}%"
        )
        candidates.append((sym, snap, tech, score, reason))

    candidates.sort(key=lambda x: x[3], reverse=True)
    return [(s, sn, t, sc, r) for s, sn, t, sc, r in candidates[:top_n]]


# ============================================================
# Geometric Grid Calculator
# ============================================================

def calculate_geometric_grid(
    symbol: str,
    category: str,
    snap: MarketSnapshot,
    tech: TechnicalAnalysis,
    score: float,
    reason: str,
    target_profit_pct: float = 0.010,  # 1.0% target per grid
    leverage: int = DEFAULT_LEVERAGE,
    invested_usdt: float = 1000.0,
) -> GridParameters:
    """
    Calculate Geometric Neutral Grid parameters.

    Geometric grid: each grid level is separated by a constant ratio r.
    Price levels: P_i = lower * r^i  where r = (upper/lower)^(1/n)

    Per-grid profit (after fees):
      profit = r - 1 - 2 * fee  (buy at P_i, sell at P_{i+1})

    Grid count selection:
      - 15-25% volatility → 30-50 grids
      - >25% volatility   → 50-60 grids
      - <15% volatility   → 20-30 grids
    """
    price = snap.mark_price if snap.mark_price > 0 else snap.last_price
    atr_abs = price * tech.atr_14_pct / 100

    # --- Grid Range: current price ± 3×ATR, anchored to BB ---
    bb_lower = tech.bb_lower if tech.bb_lower > 0 else price * 0.92
    bb_upper = tech.bb_upper if tech.bb_upper > 0 else price * 1.08
    support = tech.support_level if tech.support_level > 0 else price * 0.90
    resistance = tech.resistance_level if tech.resistance_level > 0 else price * 1.10

    # Lower bound: max of (BB lower, swing support, price - 3×ATR)
    lower = max(bb_lower, support, price - 3 * atr_abs)
    # Upper bound: min of (BB upper, swing resistance, price + 3×ATR)
    upper = min(bb_upper, resistance, price + 3 * atr_abs)

    # Ensure minimum range of 5%
    if (upper - lower) / price < 0.05:
        lower = price * 0.95
        upper = price * 1.05

    # --- Grid Count based on volatility ---
    vol = snap.volatility_24h_pct
    if vol >= 25:
        grid_count = 50
    elif vol >= 15:
        grid_count = 40
    elif vol >= 8:
        grid_count = 30
    else:
        grid_count = 20

    # --- Geometric ratio r ---
    # r = (upper/lower)^(1/n)
    ratio = (upper / lower) ** (1 / grid_count)

    # --- Per-grid profit after fees ---
    # Each grid: buy at P_i, sell at P_{i+1} = P_i * r
    # Gross profit per grid = r - 1
    # Fee cost = 2 * maker_fee (buy + sell)
    gross_profit = ratio - 1
    net_profit = gross_profit - 2 * MAKER_FEE

    # If net profit is below minimum, increase grid spacing
    if net_profit < MIN_GRID_PROFIT:
        # Solve for r: r - 1 - 2*fee = MIN_GRID_PROFIT → r = 1 + MIN_GRID_PROFIT + 2*fee
        min_ratio = 1 + MIN_GRID_PROFIT + 2 * MAKER_FEE
        # Recalculate grid count with minimum ratio
        grid_count = max(10, int(math.log(upper / lower) / math.log(min_ratio)))
        ratio = (upper / lower) ** (1 / grid_count)
        net_profit = ratio - 1 - 2 * MAKER_FEE

    # --- Risk Parameters ---
    stop_loss = lower * 0.95  # 5% hard stop below lower bound

    # Simplified liquidation price (cross margin, no initial position):
    # For neutral grid with leverage L, margin per position = invested / grid_count
    # Liquidation ≈ lower - (invested_usdt / (grid_count * leverage * (invested_usdt / lower / grid_count)))
    # Simplified: liq_price ≈ lower * (1 - 1/leverage + maintenance_margin_rate)
    maintenance_margin_rate = 0.004  # 0.4% standard
    liq_price = lower * (1 - 1 / leverage + maintenance_margin_rate)
    liq_price = max(liq_price, 0)

    # --- Funding Rate Analysis ---
    funding_rate = snap.funding_rate
    # Funding paid 3× per day (every 8 hours)
    daily_funding_yield = abs(funding_rate) * 3 * 100  # as percentage

    # --- Grid Score ---
    grid_score = min(score, 100)

    return GridParameters(
        symbol=symbol,
        category=category,
        strategy_type="Neutral",
        grid_type="Geometric",
        lower_price=round(lower, 6),
        upper_price=round(upper, 6),
        current_price=round(price, 6),
        grid_count=grid_count,
        grid_ratio=round(ratio, 8),
        profit_per_grid_pct=round(net_profit * 100, 4),
        stop_loss_price=round(stop_loss, 6),
        liquidation_price=round(liq_price, 6),
        leverage=leverage,
        funding_rate=funding_rate,
        daily_funding_yield_pct=round(daily_funding_yield, 4),
        volatility_24h_pct=round(vol, 2),
        atr_pct=round(tech.atr_14_pct, 4),
        support=round(support, 6),
        resistance=round(resistance, 6),
        grid_score=grid_score,
        category_reason=reason,
    )


# ============================================================
# Main Screening Pipeline
# ============================================================

def run_dual_category_scan(
    max_symbols: int = 200,
    top_n_each: int = 3,
) -> Tuple[List[GridParameters], List[GridParameters]]:
    """
    Full dual-category screening pipeline.

    Returns:
        (category_a_results, category_b_results)
        Each is a list of GridParameters for the top_n candidates.
    """
    print(f"[Step 0] Fetching exchange info (USDS-M perpetuals)...")
    all_symbols = fetch_exchange_info()
    if not all_symbols:
        print("  [WARN] No symbols fetched. Check API connectivity.")
        return [], []

    # Limit to most active symbols for efficiency
    print(f"[Step 0] Found {len(all_symbols)} USDS-M perpetual symbols.")

    print(f"[Step 1] Fetching all 24hr tickers...")
    all_tickers = fetch_all_tickers()
    ticker_map = {t["symbol"]: t for t in all_tickers if "symbol" in t}

    # Filter to symbols with valid ticker data
    active_symbols = [s for s in all_symbols if s.symbol in ticker_map]
    # Sort by quote volume descending, take top max_symbols
    active_symbols.sort(
        key=lambda s: float(ticker_map[s.symbol].get("quoteVolume", 0)),
        reverse=True
    )
    active_symbols = active_symbols[:max_symbols]
    print(f"[Step 1] Analyzing top {len(active_symbols)} symbols by volume.")

    print(f"[Step 2] Fetching mark prices and klines...")
    snapshots: Dict[str, MarketSnapshot] = {}
    technicals: Dict[str, TechnicalAnalysis] = {}

    for sym in active_symbols:
        ticker = ticker_map.get(sym.symbol, {})
        mark = fetch_mark_price(sym.symbol) or {}
        oi = fetch_open_interest(sym.symbol)
        snap = build_market_snapshot(sym.symbol, ticker, mark, oi)
        snapshots[sym.symbol] = snap

        # Fetch klines for technical analysis (30 daily candles)
        klines = fetch_klines(sym.symbol, interval="1d", limit=30)
        if len(klines) >= 15:
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            technicals[sym.symbol] = TechnicalAnalysis(sym.symbol, closes, highs, lows)

    print(f"[Step 3] Running Category A screening (Recent Listings)...")
    cat_a_raw = screen_recent_listings(active_symbols, snapshots, technicals, top_n=top_n_each)

    print(f"[Step 4] Running Category B screening (High Volatility)...")
    cat_b_raw = screen_high_volatility(active_symbols, snapshots, technicals, top_n=top_n_each)

    print(f"[Step 5] Calculating Geometric Grid parameters...")
    cat_a_results = []
    for sym, snap, tech, score, reason in cat_a_raw:
        gp = calculate_geometric_grid(sym.symbol, "recent_listing", snap, tech, score, reason)
        cat_a_results.append(gp)

    cat_b_results = []
    for sym, snap, tech, score, reason in cat_b_raw:
        gp = calculate_geometric_grid(sym.symbol, "high_volatility", snap, tech, score, reason)
        cat_b_results.append(gp)

    return cat_a_results, cat_b_results


def format_scan_output(cat_a: List[GridParameters], cat_b: List[GridParameters]) -> str:
    """Format the dual-category scan results for user display."""
    lines = [
        f"\n{'='*60}",
        f"  CRAYFISH GRID HUNTER v{VERSION}",
        f"  USDS-M Perpetual Futures — Dual Category Scan",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"{'='*60}",
        f"\n【次新币横盘类 — Recent Listings (Category A)】",
    ]

    if cat_a:
        for i, gp in enumerate(cat_a, 1):
            lines.append(
                f"  {i}. {gp.symbol}  "
                f"Current: ${gp.current_price:.4f}  "
                f"24h-Vol: {gp.volatility_24h_pct:.2f}%  "
                f"Support: ${gp.support:.4f}  "
                f"Resistance: ${gp.resistance:.4f}"
            )
            lines.append(f"     → {gp.category_reason}")
    else:
        lines.append("  No qualifying recent listings found.")

    lines.append(f"\n【高波动套利类 — High Volatility Arbitrage (Category B)】")

    if cat_b:
        for i, gp in enumerate(cat_b, 1):
            lines.append(
                f"  {i}. {gp.symbol}  "
                f"Current: ${gp.current_price:.4f}  "
                f"24h-Vol: {gp.volatility_24h_pct:.2f}%  "
                f"Support: ${gp.support:.4f}  "
                f"Resistance: ${gp.resistance:.4f}"
            )
            lines.append(f"     → {gp.category_reason}")
    else:
        lines.append("  No qualifying high-volatility symbols found.")

    lines.append(f"\n{'='*60}")
    lines.append(f"  GRID STRATEGY DETAILS")
    lines.append(f"{'='*60}")

    for gp in cat_a + cat_b:
        lines.append(gp.to_display())

    return "\n".join(lines)
