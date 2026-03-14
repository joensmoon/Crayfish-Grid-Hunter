"""
Crayfish Grid Hunter v5.2 — Futures Grid Engine
================================================
Core engine for USDS-M Perpetual Futures grid trading.

Two-category dual screening:
  Category A — 次新币横盘类 (Recent Contract Listings):
      Contract onboarded ≤ 90 days, volume shrinkage, narrow consolidation.
  Category B — 高波动套利类 (High Volatility Arbitrage):
      Market cap $200M–$1B, 24h turnover > 50%, RV high, strong volume.

Grid Strategy:
  - Type:      Geometric (equal-ratio) — industry standard for volatile assets
  - Direction: Neutral (no initial position bias)
  - Profit:    0.8%–1.2% per grid after fees (0.04% maker)
  - Risk:      5% hard stop-loss below lower bound + liquidation price warning
  - Funding:   Negative funding rate bonus calculation for long-biased grids

Official Skills used (unmodified):
  - derivatives-trading-usds-futures  (fapi.binance.com)
  - query-token-info                  (web3.binance.com — market cap data)
  - trading-signal                    (web3.binance.com — smart money)
  - query-token-audit                 (web3.binance.com — security)
  - assets                            (binance.com — fee optimization)
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
VERSION = "5.2.0"
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

# Category A thresholds
CONTRACT_RECENT_DAYS = 90        # Contract onboarded within 90 days
VOLUME_SHRINK_RATIO = 0.50       # 24h vol < 50% of 7-day average
ATR_SIDEWAYS_PCT = 2.0           # ATR(14) < 2% → sideways
BB_WIDTH_SIDEWAYS = 5.0          # BB width < 5% → narrow range
ADX_SIDEWAYS = 20                # ADX(14) < 20 → no trend

# Category B thresholds
MCAP_MIN = 200_000_000           # $200M minimum market cap
MCAP_MAX = 1_000_000_000         # $1B maximum market cap
TURNOVER_MIN = 0.50              # 24h volume / market cap > 50%
HIGH_VOL_RV_MIN = 15.0           # Realized volatility > 15% annualized

# ============================================================
# Data Structures
# ============================================================

@dataclass
class FuturesSymbol:
    """Represents a USDS-M perpetual futures contract."""
    symbol: str
    base_asset: str
    onboard_date: int        # Unix ms — contract listing time on Binance Futures
    contract_type: str       # PERPETUAL
    price_precision: int
    qty_precision: int
    tick_size: float
    step_size: float

    @property
    def contract_age_days(self) -> float:
        """Days since this contract was listed on Binance Futures."""
        return (time.time() * 1000 - self.onboard_date) / (1000 * 86400)

    @property
    def is_recent_contract(self) -> bool:
        """True if the contract was listed within CONTRACT_RECENT_DAYS."""
        return self.contract_age_days <= CONTRACT_RECENT_DAYS + 0.01  # tolerance for floating-point edge


@dataclass
class MarketSnapshot:
    """Real-time market data from derivatives + premiumIndex + openInterest."""
    symbol: str
    mark_price: float
    index_price: float
    last_price: float
    price_change_pct_24h: float
    volume_24h: float          # Base asset volume
    quote_volume_24h: float    # USDT volume
    open_interest: float       # Open interest in base asset
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
        """Volume/Open Interest ratio — proxy for derivatives turnover."""
        if self.open_interest > 0:
            return self.quote_volume_24h / self.open_interest
        return 0.0


@dataclass
class TokenMarketData:
    """Market cap and turnover data from query-token-info skill."""
    symbol: str
    market_cap: float          # USD
    volume_24h_usd: float      # USD (on-chain + CEX aggregated)
    create_time: Optional[int] = None  # Token creation time on chain (ms)

    @property
    def turnover_rate(self) -> float:
        """24h turnover rate = volume / market_cap."""
        if self.market_cap > 0:
            return self.volume_24h_usd / self.market_cap
        return 0.0


@dataclass
class TechnicalAnalysis:
    """Technical indicators computed from daily klines."""
    symbol: str
    closes: List[float]
    highs: List[float]
    lows: List[float]
    volumes: List[float] = field(default_factory=list)

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
        return ((4 * std) / sma * 100) if sma > 0 else 0.0

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
        return daily_std * math.sqrt(365) * 100

    @property
    def adx_14(self) -> float:
        """Simplified ADX(14) — values < 20 indicate sideways market."""
        if len(self.closes) < 15:
            return 25.0
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
    def volume_shrinkage_ratio(self) -> float:
        """Current 24h volume vs 7-day average volume.
        A ratio < 0.5 means volume has shrunk to below 50% of the 7-day average.
        """
        if not self.volumes or len(self.volumes) < 2:
            return 1.0
        # Last element = current 24h volume, previous 7 = 7-day average
        if len(self.volumes) >= 8:
            avg_7d = sum(self.volumes[-8:-1]) / 7
        else:
            avg_7d = sum(self.volumes[:-1]) / max(len(self.volumes) - 1, 1)
        if avg_7d <= 0:
            return 1.0
        return self.volumes[-1] / avg_7d


@dataclass
class GridParameters:
    """Complete Geometric Neutral Grid parameters for a futures symbol."""
    symbol: str
    category: str               # "recent_contract" | "high_volatility"
    strategy_type: str = "Neutral"
    grid_type: str = "Geometric"

    lower_price: float = 0.0
    upper_price: float = 0.0
    current_price: float = 0.0

    grid_count: int = 0
    grid_ratio: float = 0.0
    profit_per_grid_pct: float = 0.0

    stop_loss_price: float = 0.0
    liquidation_price: float = 0.0
    leverage: int = DEFAULT_LEVERAGE

    funding_rate: float = 0.0
    daily_funding_yield_pct: float = 0.0

    volatility_24h_pct: float = 0.0
    atr_pct: float = 0.0
    support: float = 0.0
    resistance: float = 0.0

    grid_score: float = 0.0
    category_reason: str = ""

    # Category B specific
    market_cap: float = 0.0
    turnover_rate_pct: float = 0.0

    def to_display(self) -> str:
        """Format grid parameters for user-facing output."""
        funding_note = ""
        if self.funding_rate < 0:
            funding_note = (
                f"\n  Funding提醒    : funding rate {self.funding_rate*100:.4f}%"
                f"，多头网格每日预期收益 +{abs(self.daily_funding_yield_pct):.3f}%"
            )
        elif self.funding_rate > 0.001:
            funding_note = (
                f"\n  Funding提醒    : funding rate {self.funding_rate*100:.4f}%"
                f"，空头网格每日预期收益 +{self.daily_funding_yield_pct:.3f}%"
            )
        else:
            funding_note = (
                f"\n  Funding提醒    : funding rate {self.funding_rate*100:.4f}%（中性）"
            )

        mcap_line = ""
        if self.market_cap > 0:
            mcap_line = f"\n  市值           : ${self.market_cap/1e6:.0f}M  换手率: {self.turnover_rate_pct:.1f}%"

        return (
            f"\n{'='*58}"
            f"\n  针对 {self.symbol}："
            f"\n{'='*58}"
            f"\n  策略类型       : 合约中性网格（{self.strategy_type}）"
            f"\n  网格类型       : {self.grid_type} 等比"
            f"\n  当前价格       : ${self.current_price:.4f}"
            f"\n  网格区间       : ${self.lower_price:.4f} — ${self.upper_price:.4f}"
            f"\n  网格数量       : {self.grid_count} grids"
            f"\n  网格比率(r)    : {self.grid_ratio:.6f}"
            f"\n  单格利润率     : {self.profit_per_grid_pct:.2f}%（扣 {MAKER_FEE*100:.2f}% 手续费后）"
            f"\n  杠杆倍数       : {self.leverage}×"
            f"\n  5%硬止损位     : ${self.stop_loss_price:.4f}（下轨下方5%）"
            f"\n  强平价估算     : ${self.liquidation_price:.4f}"
            f"\n  24h波动率      : {self.volatility_24h_pct:.2f}%"
            f"\n  支撑 / 压力    : ${self.support:.4f} / ${self.resistance:.4f}"
            f"{mcap_line}"
            f"{funding_note}"
            f"\n  网格评分       : {self.grid_score:.0f}/100"
            f"\n  分类依据       : {self.category_reason}"
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
    _active_fapi = FAPI_BASE
    return _active_fapi


def fetch_exchange_info() -> List[FuturesSymbol]:
    """GET /fapi/v1/exchangeInfo — all USDS-M perpetual symbols."""
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
            tick_size, step_size = 0.01, 0.001
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


def fetch_all_tickers() -> List[dict]:
    """GET /fapi/v1/ticker/24hr — all tickers in one call."""
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


def fetch_mark_price(symbol: str) -> Optional[dict]:
    """GET /fapi/v1/premiumIndex — mark price + funding rate."""
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
    except Exception:
        return None


def fetch_klines(symbol: str, interval: str = "1d", limit: int = 30) -> List[list]:
    """GET /fapi/v1/klines — candlestick data."""
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
    except Exception:
        return []


def fetch_open_interest(symbol: str) -> float:
    """GET /fapi/v1/openInterest — current open interest."""
    base = get_fapi_base()
    try:
        r = requests.get(f"{base}/fapi/v1/openInterest",
                         params={"symbol": symbol}, timeout=10,
                         headers={"User-Agent": USER_AGENT_DERIV})
        r.raise_for_status()
        return float(r.json().get("openInterest", 0))
    except Exception:
        return 0.0


# ============================================================
# API Layer — query-token-info skill (market cap data)
# ============================================================

def fetch_token_market_data(base_asset: str) -> Optional[TokenMarketData]:
    """
    Use the official query-token-info skill to get market cap data.

    API: GET /bapi/defi/v5/public/wallet-direct/buw/wallet/market/token/search
    Skill: query-token-info (binance-web3)
    Authentication: Not required
    """
    cached = _get_cache(f"token_info_{base_asset}")
    if cached:
        return cached

    url = (
        f"{WEB3_BASE}/bapi/defi/v5/public/wallet-direct/"
        f"buw/wallet/market/token/search"
    )
    try:
        r = requests.get(url,
                         params={"keyword": base_asset, "orderBy": "volume24h"},
                         timeout=10,
                         headers={
                             "Accept-Encoding": "identity",
                             "User-Agent": USER_AGENT_WEB3,
                         })
        r.raise_for_status()
        data = r.json()
        tokens = data.get("data", [])
        if not tokens:
            return None

        # Find the best match: exact symbol match with highest market cap
        best = None
        for t in tokens:
            sym = t.get("symbol", "").upper()
            if sym == base_asset.upper() or sym == f"${base_asset.upper()}":
                mc = float(t.get("marketCap", 0) or 0)
                if best is None or mc > best.market_cap:
                    best = TokenMarketData(
                        symbol=base_asset,
                        market_cap=mc,
                        volume_24h_usd=float(t.get("volume24h", 0) or 0),
                        create_time=t.get("createTime"),
                    )

        if best is None and tokens:
            t = tokens[0]
            best = TokenMarketData(
                symbol=base_asset,
                market_cap=float(t.get("marketCap", 0) or 0),
                volume_24h_usd=float(t.get("volume24h", 0) or 0),
                create_time=t.get("createTime"),
            )

        if best:
            _set_cache(f"token_info_{base_asset}", best)
        return best
    except Exception as e:
        print(f"  [WARN] query-token-info {base_asset}: {e}")
        return None


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


def screen_recent_contracts(
    symbols: List[FuturesSymbol],
    snapshots: Dict[str, MarketSnapshot],
    technicals: Dict[str, TechnicalAnalysis],
    top_n: int = 3,
) -> List[Tuple[FuturesSymbol, MarketSnapshot, TechnicalAnalysis, float, str]]:
    """
    Category A — 次新币横盘类 (Recent Contract Listings)

    Criteria:
      1. Contract onboarded ≤ 90 days (onboardDate)
      2. Volume shrinkage: 24h volume < 50% of 7-day average
      3. Sideways: ATR(14) < 2% OR BB_width < 5% OR ADX(14) < 20
    """
    candidates = []
    for sym in symbols:
        if not sym.is_recent_contract:
            continue
        snap = snapshots.get(sym.symbol)
        tech = technicals.get(sym.symbol)
        if not snap or not tech:
            continue
        if snap.last_price <= 0:
            continue

        # Volume shrinkage check
        vol_ratio = tech.volume_shrinkage_ratio
        has_volume_shrinkage = vol_ratio < VOLUME_SHRINK_RATIO

        # Sideways check: at least one indicator must confirm
        is_sideways = (
            tech.atr_14_pct < ATR_SIDEWAYS_PCT or
            tech.bb_width_pct < BB_WIDTH_SIDEWAYS or
            tech.adx_14 < ADX_SIDEWAYS
        )

        if not (has_volume_shrinkage and is_sideways):
            continue

        # Score: sideways strength + volume shrinkage + recency
        sideways_score = 0.0
        sideways_score += max(0, (ATR_SIDEWAYS_PCT - tech.atr_14_pct) / ATR_SIDEWAYS_PCT * 25)
        sideways_score += max(0, (BB_WIDTH_SIDEWAYS - tech.bb_width_pct) / BB_WIDTH_SIDEWAYS * 25)
        sideways_score += max(0, (ADX_SIDEWAYS - tech.adx_14) / ADX_SIDEWAYS * 20) if tech.adx_14 < ADX_SIDEWAYS else 0

        # Volume shrinkage bonus: more shrinkage = better consolidation
        shrink_score = max(0, (VOLUME_SHRINK_RATIO - vol_ratio) / VOLUME_SHRINK_RATIO * 15)

        # Recency bonus
        recency_bonus = max(0, (CONTRACT_RECENT_DAYS - sym.contract_age_days) / CONTRACT_RECENT_DAYS * 15)

        score = sideways_score + shrink_score + recency_bonus

        reason = (
            f"合约上线{sym.contract_age_days:.0f}天; "
            f"成交量萎缩至{vol_ratio*100:.0f}%; "
            f"ATR={tech.atr_14_pct:.2f}%, BB宽={tech.bb_width_pct:.2f}%, ADX={tech.adx_14:.1f}"
        )
        candidates.append((sym, snap, tech, score, reason))

    candidates.sort(key=lambda x: x[3], reverse=True)
    return candidates[:top_n]


def screen_high_volatility(
    symbols: List[FuturesSymbol],
    snapshots: Dict[str, MarketSnapshot],
    technicals: Dict[str, TechnicalAnalysis],
    token_data: Dict[str, TokenMarketData],
    top_n: int = 3,
) -> List[Tuple[FuturesSymbol, MarketSnapshot, TechnicalAnalysis, float, str]]:
    """
    Category B — 高波动套利类 (High Volatility Arbitrage)

    Criteria:
      1. Market cap $200M – $1B (from query-token-info)
      2. 24h turnover rate > 50% (quoteVolume / marketCap)
      3. Realized volatility > 15% annualized
      4. Volume confirmation: quoteVolume > $10M (active trading)
    """
    candidates = []
    for sym in symbols:
        snap = snapshots.get(sym.symbol)
        tech = technicals.get(sym.symbol)
        tdata = token_data.get(sym.base_asset)
        if not snap or not tech:
            continue
        if snap.last_price <= 0:
            continue

        # Market cap filter (from query-token-info)
        mcap = 0.0
        if tdata and tdata.market_cap > 0:
            mcap = tdata.market_cap
        else:
            continue  # No market cap data → skip

        if not (MCAP_MIN <= mcap <= MCAP_MAX):
            continue

        # Turnover rate: use futures quoteVolume / market cap
        turnover = snap.quote_volume_24h / mcap if mcap > 0 else 0
        if turnover < TURNOVER_MIN:
            continue

        # Realized volatility
        rv = tech.realized_volatility_pct
        if rv < HIGH_VOL_RV_MIN:
            continue

        # Volume confirmation: at least $10M in 24h quote volume
        if snap.quote_volume_24h < 10_000_000:
            continue

        # Score
        rv_score = min(rv / 50 * 30, 30)
        turnover_score = min(turnover / 2.0 * 25, 25)
        # Optimal intraday vol: 15-25% is ideal for grid trading
        intraday_vol = snap.volatility_24h_pct
        vol_score = 25 if 15 <= intraday_vol <= 25 else max(0, 25 - abs(intraday_vol - 20) * 1.5)
        # Volume strength
        vol_strength = min(snap.quote_volume_24h / 100_000_000 * 20, 20)
        score = rv_score + turnover_score + vol_score + vol_strength

        reason = (
            f"市值${mcap/1e6:.0f}M; "
            f"换手率{turnover*100:.0f}%; "
            f"RV={rv:.1f}%/yr; "
            f"24h波动={intraday_vol:.1f}%"
        )
        candidates.append((sym, snap, tech, score, reason))

    candidates.sort(key=lambda x: x[3], reverse=True)
    return candidates[:top_n]


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
    market_cap: float = 0.0,
    turnover_rate: float = 0.0,
    leverage: int = DEFAULT_LEVERAGE,
) -> GridParameters:
    """
    Calculate Geometric Neutral Grid parameters.

    Geometric grid: P_i = lower * r^i  where r = (upper/lower)^(1/n)
    Per-grid profit: profit = r - 1 - 2 * fee
    """
    price = snap.mark_price if snap.mark_price > 0 else snap.last_price
    atr_abs = price * tech.atr_14_pct / 100

    # Grid Range
    bb_lower = tech.bb_lower if tech.bb_lower > 0 else price * 0.92
    bb_upper = tech.bb_upper if tech.bb_upper > 0 else price * 1.08
    support = tech.support_level if tech.support_level > 0 else price * 0.90
    resistance = tech.resistance_level if tech.resistance_level > 0 else price * 1.10

    lower = max(bb_lower, support, price - 3 * atr_abs)
    upper = min(bb_upper, resistance, price + 3 * atr_abs)

    if (upper - lower) / price < 0.05:
        lower = price * 0.95
        upper = price * 1.05

    # Grid Count based on volatility
    vol = snap.volatility_24h_pct
    if vol >= 25:
        grid_count = 50
    elif vol >= 15:
        grid_count = 40
    elif vol >= 8:
        grid_count = 30
    else:
        grid_count = 20

    # Geometric ratio
    ratio = (upper / lower) ** (1 / grid_count)
    gross_profit = ratio - 1
    net_profit = gross_profit - 2 * MAKER_FEE

    # Minimum profit enforcement
    if net_profit < MIN_GRID_PROFIT:
        min_ratio = 1 + MIN_GRID_PROFIT + 2 * MAKER_FEE
        grid_count = max(10, int(math.log(upper / lower) / math.log(min_ratio)))
        ratio = (upper / lower) ** (1 / grid_count)
        net_profit = ratio - 1 - 2 * MAKER_FEE

    # Risk
    stop_loss = lower * 0.95
    maintenance_margin_rate = 0.004
    liq_price = lower * (1 - 1 / leverage + maintenance_margin_rate)
    liq_price = max(liq_price, 0)

    # Funding
    funding_rate = snap.funding_rate
    daily_funding_yield = abs(funding_rate) * 3 * 100

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
        grid_score=min(score, 100),
        category_reason=reason,
        market_cap=market_cap,
        turnover_rate_pct=round(turnover_rate * 100, 1) if turnover_rate else 0.0,
    )


# ============================================================
# Main Screening Pipeline
# ============================================================

def run_dual_category_scan(
    max_symbols: int = 200,
    top_n_each: int = 3,
) -> Tuple[List[GridParameters], List[GridParameters]]:
    """Full dual-category screening pipeline."""
    print(f"[Step 0] Fetching exchange info (USDS-M perpetuals)...")
    all_symbols = fetch_exchange_info()
    if not all_symbols:
        print("  [WARN] No symbols fetched.")
        return [], []
    print(f"  Found {len(all_symbols)} USDS-M perpetual symbols.")

    print(f"[Step 0] Fetching all 24hr tickers...")
    all_tickers = fetch_all_tickers()
    ticker_map = {t["symbol"]: t for t in all_tickers if "symbol" in t}

    active_symbols = [s for s in all_symbols if s.symbol in ticker_map]
    active_symbols.sort(
        key=lambda s: float(ticker_map[s.symbol].get("quoteVolume", 0)),
        reverse=True
    )
    active_symbols = active_symbols[:max_symbols]
    print(f"  Analyzing top {len(active_symbols)} symbols by volume.")

    print(f"[Step 1] Fetching klines and mark prices...")
    snapshots: Dict[str, MarketSnapshot] = {}
    technicals: Dict[str, TechnicalAnalysis] = {}

    for sym in active_symbols:
        ticker = ticker_map.get(sym.symbol, {})
        mark = fetch_mark_price(sym.symbol) or {}
        oi = fetch_open_interest(sym.symbol)
        snap = build_market_snapshot(sym.symbol, ticker, mark, oi)
        snapshots[sym.symbol] = snap

        klines = fetch_klines(sym.symbol, interval="1d", limit=30)
        if len(klines) >= 15:
            closes = [float(k[4]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            volumes = [float(k[5]) for k in klines]  # quoteAssetVolume
            technicals[sym.symbol] = TechnicalAnalysis(
                sym.symbol, closes, highs, lows, volumes
            )

    print(f"[Step 2] Fetching market cap data via query-token-info...")
    token_data: Dict[str, TokenMarketData] = {}
    for sym in active_symbols:
        tdata = fetch_token_market_data(sym.base_asset)
        if tdata:
            token_data[sym.base_asset] = tdata

    print(f"[Step 3] Running Category A screening (次新币横盘类)...")
    cat_a_raw = screen_recent_contracts(active_symbols, snapshots, technicals, top_n=top_n_each)

    print(f"[Step 4] Running Category B screening (高波动套利类)...")
    cat_b_raw = screen_high_volatility(active_symbols, snapshots, technicals, token_data, top_n=top_n_each)

    print(f"[Step 5] Calculating Geometric Grid parameters...")
    cat_a_results = []
    for sym, snap, tech, score, reason in cat_a_raw:
        gp = calculate_geometric_grid(sym.symbol, "recent_contract", snap, tech, score, reason)
        cat_a_results.append(gp)

    cat_b_results = []
    for sym, snap, tech, score, reason in cat_b_raw:
        tdata = token_data.get(sym.base_asset)
        mcap = tdata.market_cap if tdata else 0
        turnover = snap.quote_volume_24h / mcap if mcap > 0 else 0
        gp = calculate_geometric_grid(
            sym.symbol, "high_volatility", snap, tech, score, reason,
            market_cap=mcap, turnover_rate=turnover,
        )
        cat_b_results.append(gp)

    return cat_a_results, cat_b_results


def format_scan_output(cat_a: List[GridParameters], cat_b: List[GridParameters]) -> str:
    """Format the dual-category scan results for user display."""
    lines = [
        f"\n{'='*60}",
        f"  CRAYFISH GRID HUNTER v{VERSION}",
        f"  USDS-M 永续合约 — 双分类筛选结果",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"{'='*60}",
        f"\n【次新币横盘类 — Category A】",
    ]

    if cat_a:
        for i, gp in enumerate(cat_a, 1):
            lines.append(
                f"  {i}. {gp.symbol}  "
                f"当前价 ${gp.current_price:.4f}  "
                f"24h波动率 {gp.volatility_24h_pct:.2f}%  "
                f"支撑 ${gp.support:.4f}  "
                f"压力 ${gp.resistance:.4f}"
            )
            lines.append(f"     → {gp.category_reason}")
    else:
        lines.append("  暂无符合条件的次新币横盘标的。")

    lines.append(f"\n【高波动套利类 — Category B】")

    if cat_b:
        for i, gp in enumerate(cat_b, 1):
            lines.append(
                f"  {i}. {gp.symbol}  "
                f"当前价 ${gp.current_price:.4f}  "
                f"24h波动率 {gp.volatility_24h_pct:.2f}%  "
                f"支撑 ${gp.support:.4f}  "
                f"压力 ${gp.resistance:.4f}"
            )
            lines.append(f"     → {gp.category_reason}")
    else:
        lines.append("  暂无符合条件的高波动套利标的。")

    lines.append(f"\n{'='*60}")
    lines.append(f"  网格策略详情")
    lines.append(f"{'='*60}")

    for gp in cat_a + cat_b:
        lines.append(gp.to_display())

    return "\n".join(lines)
