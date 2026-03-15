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
VERSION = "2.3.0"
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
# User-Customizable Parameters (v5.3)
# ============================================================

@dataclass
class UserConfig:
    """
    User-customizable screening and grid parameters.

    All fields have sensible defaults matching the standard strategy.
    Users can override any subset of parameters via natural language:

        "帮我筛选次新币网格，市值范围5亿到20亿"
        → UserConfig(mcap_min=500_000_000, mcap_max=2_000_000_000)

        "高波动套利，换手率30%以上，止损8%"
        → UserConfig(turnover_min=0.30, stop_loss_pct=8.0)
    """
    # --- Category A: Recent Contract Listings ---
    contract_recent_days: int = CONTRACT_RECENT_DAYS
    volume_shrink_ratio: float = VOLUME_SHRINK_RATIO
    atr_sideways_pct: float = ATR_SIDEWAYS_PCT
    bb_width_sideways: float = BB_WIDTH_SIDEWAYS
    adx_sideways: float = ADX_SIDEWAYS

    # --- Category B: High Volatility Arbitrage ---
    mcap_min: float = MCAP_MIN
    mcap_max: float = MCAP_MAX
    turnover_min: float = TURNOVER_MIN
    rv_min: float = HIGH_VOL_RV_MIN
    min_quote_volume: float = 10_000_000

    # --- Grid Parameters ---
    leverage: int = DEFAULT_LEVERAGE
    min_grid_profit: float = MIN_GRID_PROFIT
    max_grid_profit: float = MAX_GRID_PROFIT
    stop_loss_pct: float = 5.0
    max_exposure: float = MAX_ACCOUNT_EXPOSURE

    # --- Screening ---
    max_symbols: int = 200
    top_n: int = 3

    # --- Backtest ---
    backtest_days: int = 30
    backtest_interval: str = "1h"

    def validate(self) -> List[str]:
        """Validate user config and return list of warnings."""
        warnings = []
        if self.leverage > 20:
            warnings.append(f"杠杆{self.leverage}×过高，建议不超过20×")
        if self.leverage < 1:
            warnings.append("杠杆必须≥1")
        if self.stop_loss_pct < 1:
            warnings.append(f"止损{self.stop_loss_pct}%过小，可能频繁触发")
        if self.stop_loss_pct > 20:
            warnings.append(f"止损{self.stop_loss_pct}%过大，风险控制不足")
        if self.min_grid_profit < 0.003:
            warnings.append(f"单格利润{self.min_grid_profit*100:.1f}%过低，可能无法覆盖手续费")
        if self.mcap_min >= self.mcap_max:
            warnings.append(f"市值下限(${self.mcap_min/1e6:.0f}M)≥上限(${self.mcap_max/1e6:.0f}M)")
        if self.turnover_min > 5.0:
            warnings.append(f"换手率{self.turnover_min*100:.0f}%阈值过高，可能无结果")
        if self.top_n < 1:
            warnings.append("top_n必须≥1")
        return warnings

    def to_display(self) -> str:
        """Format config as readable summary."""
        lines = [
            "当前自定义参数:",
            f"  Category A: 合约≤{self.contract_recent_days}天, 量缩<{self.volume_shrink_ratio*100:.0f}%, ATR<{self.atr_sideways_pct}%, BB<{self.bb_width_sideways}%, ADX<{self.adx_sideways}",
            f"  Category B: 市值${self.mcap_min/1e6:.0f}M-${self.mcap_max/1e6:.0f}M, 换手率>{self.turnover_min*100:.0f}%, RV>{self.rv_min}%",
            f"  网格: {self.leverage}×杠杆, 利润{self.min_grid_profit*100:.1f}%-{self.max_grid_profit*100:.1f}%, 止损{self.stop_loss_pct}%",
            f"  筛选: Top {self.top_n}, 分析前{self.max_symbols}个币种",
        ]
        return "\n".join(lines)


# Default config instance
DEFAULT_CONFIG = UserConfig()


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
        Uses the most recent complete day vs the prior 7-day average.
        Excludes the last candle (may be incomplete) when computing the baseline.
        """
        # Allow manual override for testing
        if hasattr(self, '_volume_shrinkage_ratio'):
            return self._volume_shrinkage_ratio
        if not self.volumes or len(self.volumes) < 3:
            return 1.0
        # Use the second-to-last candle as "current day" to avoid incomplete candle
        # Use candles [-9:-2] (7 days) as the baseline average
        current_vol = self.volumes[-2]  # Most recent complete day
        if len(self.volumes) >= 9:
            baseline = self.volumes[-9:-2]  # 7 complete days before current
        else:
            baseline = self.volumes[:-2]    # All available days before current
        avg_7d = sum(baseline) / len(baseline) if baseline else 0
        if avg_7d <= 0:
            return 1.0
        return current_vol / avg_7d


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

        # Price-in-range validation
        price_in_range = self.lower_price < self.current_price < self.upper_price
        range_status = "✅ 在区间内" if price_in_range else "⚠️ 在区间外！"
        range_pct = (self.upper_price - self.lower_price) / self.current_price * 100

        # Grid count recommendation hint
        vol = self.volatility_24h_pct
        if vol >= 25:
            grid_hint = "高波动建议50格"
        elif vol >= 15:
            grid_hint = "中高波动建议40格"
        elif vol >= 8:
            grid_hint = "中波动建议30格"
        else:
            grid_hint = "低波动建议20格"

        return (
            f"\n{'='*62}"
            f"\n  针对 {self.symbol}："
            f"\n{'='*62}"
            f"\n  策略类型       : 合约中性网格（{self.strategy_type}）"
            f"\n  网格类型       : {self.grid_type} 等比"
            f"\n  当前价格       : ${self.current_price:.4f}  [{range_status}]"
            f"\n  网格区间       : ${self.lower_price:.4f} — ${self.upper_price:.4f}  (宽度 {range_pct:.1f}%)"
            f"\n  网格数量       : {self.grid_count} 格  ({grid_hint})"
            f"\n  网格比率(r)    : {self.grid_ratio:.6f}"
            f"\n  单格利润率     : {self.profit_per_grid_pct:.2f}%（扣 {MAKER_FEE*100:.2f}% 手续费后）"
            f"\n  杠杆倍数       : {self.leverage}×"
            f"\n  5%硬止损位     : ${self.stop_loss_price:.4f}（下轨下方5%）"
            f"\n  强平价估算     : ${self.liquidation_price:.4f}（估算值，以交易所显示为准）"
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

        # IMPORTANT: Do NOT use fallback to tokens[0].
        # tokens[0] may be a completely different token that happens to appear
        # first in Web3 search results (e.g. searching "ACE" might return "ACEME").
        # Only use data when the symbol is an exact match to avoid cross-contamination.
        # All candidates in screen_high_volatility already come from fapi exchangeInfo
        # (USDS-M whitelist), so we only need accurate market cap data for those symbols.

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
    config: Optional[UserConfig] = None,
) -> List[Tuple[FuturesSymbol, MarketSnapshot, TechnicalAnalysis, float, str]]:
    """
    Category A — 次新币横盘类 (Recent Contract Listings)

    Criteria:
      1. Contract onboarded ≤ 90 days (onboardDate)
      2. Volume shrinkage: 24h volume < 50% of 7-day average
      3. Sideways: ATR(14) < 2% OR BB_width < 5% OR ADX(14) < 20
    """
    cfg = config or DEFAULT_CONFIG
    candidates = []
    for sym in symbols:
        # Use config threshold for contract age
        if sym.contract_age_days > cfg.contract_recent_days + 0.01:
            continue
        snap = snapshots.get(sym.symbol)
        tech = technicals.get(sym.symbol)
        if not snap or not tech:
            continue
        if snap.last_price <= 0:
            continue

        # Volume shrinkage check (using config threshold)
        vol_ratio = tech.volume_shrinkage_ratio
        has_volume_shrinkage = vol_ratio < cfg.volume_shrink_ratio

        # Sideways check:
        # ADX is the primary trend filter — if ADX >= threshold, it's trending, exclude.
        # ATR and BB width are secondary confirmations (at least one must show low volatility).
        adx_ok = tech.adx_14 < cfg.adx_sideways
        low_vol_confirmed = (
            tech.atr_14_pct < cfg.atr_sideways_pct or
            tech.bb_width_pct < cfg.bb_width_sideways
        )
        is_sideways = adx_ok and low_vol_confirmed

        if not (has_volume_shrinkage and is_sideways):
            continue

        # Score: sideways strength + volume shrinkage + recency
        sideways_score = 0.0
        sideways_score += max(0, (cfg.atr_sideways_pct - tech.atr_14_pct) / cfg.atr_sideways_pct * 25)
        sideways_score += max(0, (cfg.bb_width_sideways - tech.bb_width_pct) / cfg.bb_width_sideways * 25)
        sideways_score += max(0, (cfg.adx_sideways - tech.adx_14) / cfg.adx_sideways * 20) if tech.adx_14 < cfg.adx_sideways else 0

        # Volume shrinkage bonus: more shrinkage = better consolidation
        shrink_score = max(0, (cfg.volume_shrink_ratio - vol_ratio) / cfg.volume_shrink_ratio * 15)

        # Recency bonus
        recency_bonus = max(0, (cfg.contract_recent_days - sym.contract_age_days) / cfg.contract_recent_days * 15)

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
    config: Optional[UserConfig] = None,
) -> List[Tuple[FuturesSymbol, MarketSnapshot, TechnicalAnalysis, float, str]]:
    """
    Category B — 高波动套利类 (High Volatility Arbitrage)

    Criteria:
      1. Market cap $200M – $1B (from query-token-info)
      2. 24h turnover rate > 50% (quoteVolume / marketCap)
      3. Realized volatility > 15% annualized
      4. Volume confirmation: quoteVolume > $10M (active trading)
    """
    cfg = config or DEFAULT_CONFIG
    # NOTE: `symbols` is already filtered from fapi/v1/exchangeInfo (USDS-M perpetual
    # whitelist, status=TRADING). Every symbol here is a real listed contract.
    # The token_data dict comes from query-token-info (Web3 search).
    # We only use token_data when the symbol is an EXACT match to prevent
    # cross-contamination from similarly-named tokens in the Web3 ecosystem.
    candidates = []
    for sym in symbols:
        snap = snapshots.get(sym.symbol)
        tech = technicals.get(sym.symbol)
        tdata = token_data.get(sym.base_asset)
        if not snap or not tech:
            continue
        if snap.last_price <= 0:
            continue

        # Double-check: token_data symbol must exactly match base_asset
        # (fetch_token_market_data already enforces this, but be explicit)
        if tdata and tdata.symbol.upper() != sym.base_asset.upper():
            tdata = None

        # Market cap filter (using config thresholds)
        mcap = 0.0
        if tdata and tdata.market_cap > 0:
            mcap = tdata.market_cap
        else:
            continue  # No exact-match market cap data → skip (safe default)

        if not (cfg.mcap_min <= mcap <= cfg.mcap_max):
            continue

        # Turnover rate: use futures quoteVolume / market cap (using config threshold)
        turnover = snap.quote_volume_24h / mcap if mcap > 0 else 0
        if turnover < cfg.turnover_min:
            continue

        # Realized volatility (using config threshold)
        rv = tech.realized_volatility_pct
        if rv < cfg.rv_min:
            continue

        # Volume confirmation (using config threshold)
        if snap.quote_volume_24h < cfg.min_quote_volume:
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

    # Lower bound: take the highest of BB lower, support, and price-3ATR
    # but must not exceed current price
    lower = min(max(bb_lower, support, price - 3 * atr_abs), price * 0.99)

    # Upper bound: take the lowest of BB upper, resistance, and price+3ATR
    # but must not be below current price
    upper = max(min(bb_upper, resistance, price + 3 * atr_abs), price * 1.01)

    # Ensure minimum range of 5% centered around current price
    if (upper - lower) / price < 0.05:
        half = price * 0.025
        lower = price - half
        upper = price + half

    # Final safety: ensure lower < price < upper
    if lower >= price:
        lower = price * 0.97
    if upper <= price:
        upper = price * 1.03

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
    # If the range is too narrow to achieve MIN_GRID_PROFIT even with min grids,
    # expand the range symmetrically around the current price.
    if net_profit < MIN_GRID_PROFIT:
        min_ratio = 1 + MIN_GRID_PROFIT + 2 * MAKER_FEE
        grid_count = max(10, int(math.log(upper / lower) / math.log(min_ratio)))
        ratio = (upper / lower) ** (1 / grid_count)
        net_profit = ratio - 1 - 2 * MAKER_FEE

        # If still below minimum after reducing grid count, expand range
        if net_profit < MIN_GRID_PROFIT:
            # Calculate minimum range needed for MIN_GRID_PROFIT with 10 grids
            # min_range = min_ratio^10 - 1
            min_range_ratio = min_ratio ** 10  # upper/lower ratio needed
            half_range = (math.sqrt(min_range_ratio) - 1) * price
            lower = price - half_range
            upper = price + half_range
            grid_count = 10
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
    config: Optional[UserConfig] = None,
    show_progress: bool = True,
) -> Tuple[List[GridParameters], List[GridParameters]]:
    """
    Full dual-category screening pipeline with progress tracking.

    Parameters
    ----------
    max_symbols : int
        Maximum number of symbols to scan (sorted by volume).
    top_n_each : int
        Number of top results to return per category.
    config : UserConfig, optional
        Custom configuration. Defaults to DEFAULT_CONFIG.
    show_progress : bool
        Whether to show progress bar during data fetching.

    Returns
    -------
    Tuple[List[GridParameters], List[GridParameters]]
        (Category A results, Category B results)
    """
    try:
        from progress import ProgressBar, StepProgress, format_error
        _has_progress = True
    except ImportError:
        _has_progress = False

    def _log(msg: str):
        print(f"  {msg}")

    # Step tracker
    step_names = [
        "获取合约列表 (exchangeInfo)",
        "获取行情快照 (klines + mark price)",
        "获取市值数据 (query-token-info)",
        "Category A 筛选 (次新币横盘)",
        "Category B 筛选 (高波动套利)",
        "计算等比网格参数",
    ]
    if _has_progress:
        sp = StepProgress(step_names)
    else:
        sp = None

    def _step_start(idx, detail=""):
        if sp:
            sp.start_step(idx, detail)
        else:
            print(f"[Step {idx}] {step_names[idx]}... {detail}")

    def _step_done(idx, detail=""):
        if sp:
            sp.complete_step(idx, detail)

    def _step_fail(idx, error=""):
        if sp:
            sp.fail_step(idx, error)
        else:
            print(f"  [FAIL] Step {idx}: {error}")

    import hashlib as _hashlib
    _exec_ts = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
    _exec_id = _hashlib.md5(f"{time.time()}{VERSION}".encode()).hexdigest()[:8].upper()
    print(f"\n{'='*60}")
    print(f"  🦞 Crayfish Grid Hunter v{VERSION} — 实时扫描")
    print(f"  执行时间: {_exec_ts}  |  执行ID: {_exec_id}")
    print(f"  扫描范围: Top {max_symbols} 合约 | 返回 Top {top_n_each} / 类别")
    print(f"  数据来源: 币安官方 fapi.binance.com (实时)")
    print(f"  ⚠ 本输出由脚本实时生成，任何未含执行ID的结果均为无效")
    print(f"{'='*60}\n")

    # --- Step 0: Exchange Info ---
    _step_start(0)
    all_symbols = fetch_exchange_info()
    if not all_symbols:
        _step_fail(0, "No symbols fetched")
        print(format_error("451", "exchangeInfo returned empty") if _has_progress
              else "  [WARN] No symbols fetched. Check API connectivity.")
        return [], []
    _step_done(0, f"找到 {len(all_symbols)} 个 USDS-M 永续合约")

    all_tickers = fetch_all_tickers()
    ticker_map = {t["symbol"]: t for t in all_tickers if "symbol" in t}

    active_symbols = [s for s in all_symbols if s.symbol in ticker_map]
    active_symbols.sort(
        key=lambda s: float(ticker_map[s.symbol].get("quoteVolume", 0)),
        reverse=True
    )
    active_symbols = active_symbols[:max_symbols]
    _log(f"按交易量排序，分析 Top {len(active_symbols)} 个合约")

    # --- Step 1: Klines + Mark Prices ---
    _step_start(1)
    snapshots: Dict[str, MarketSnapshot] = {}
    technicals: Dict[str, TechnicalAnalysis] = {}

    if _has_progress and show_progress:
        bar = ProgressBar(total=len(active_symbols), prefix="  获取行情数据")
    else:
        bar = None

    for i, sym in enumerate(active_symbols):
        if bar:
            bar.update(i + 1, suffix=sym.symbol)
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
            volumes = [float(k[5]) for k in klines]
            technicals[sym.symbol] = TechnicalAnalysis(
                sym.symbol, closes, highs, lows, volumes
            )

    if bar:
        bar.finish(f"已获取 {len(technicals)} 个合约的技术指标")
    _step_done(1, f"已处理 {len(snapshots)} 个快照, {len(technicals)} 个技术分析")

    # --- Step 2: Market Cap Data ---
    _step_start(2)
    token_data: Dict[str, TokenMarketData] = {}
    token_fetch_count = 0

    if _has_progress and show_progress:
        bar2 = ProgressBar(total=len(active_symbols), prefix="  获取市値数据")
    else:
        bar2 = None

    for i, sym in enumerate(active_symbols):
        if bar2:
            bar2.update(i + 1, suffix=sym.base_asset)
        tdata = fetch_token_market_data(sym.base_asset)
        if tdata:
            token_data[sym.base_asset] = tdata
            token_fetch_count += 1

    if bar2:
        bar2.finish(f"获取到 {token_fetch_count} 个代币的市値数据")

    if token_fetch_count == 0:
        _step_fail(2, "市値数据全部获取失败")
        print(format_error("token_info_empty") if _has_progress
              else "  [WARN] query-token-info returned no data. Category B may be empty.")
    else:
        _step_done(2, f"获取 {token_fetch_count} 个代币市値数据")

    cfg = config or DEFAULT_CONFIG

    # --- Step 3: Category A Screening ---
    _step_start(3)
    cat_a_raw = screen_recent_contracts(
        active_symbols, snapshots, technicals, top_n=top_n_each, config=cfg
    )
    if cat_a_raw:
        _step_done(3, f"找到 {len(cat_a_raw)} 个次新币横盘标的")
    else:
        _step_done(3, "暂无符合条件的次新币标的")

    # --- Step 4: Category B Screening ---
    _step_start(4)
    cat_b_raw = screen_high_volatility(
        active_symbols, snapshots, technicals, token_data, top_n=top_n_each, config=cfg
    )
    if cat_b_raw:
        _step_done(4, f"找到 {len(cat_b_raw)} 个高波动套利标的")
    else:
        _step_done(4, "暂无符合条件的高波动标的")

    # --- Step 5: Grid Calculation ---
    _step_start(5)
    cat_a_results = []
    for sym, snap, tech, score, reason in cat_a_raw:
        gp = calculate_geometric_grid(
            sym.symbol, "recent_contract", snap, tech, score, reason,
            leverage=cfg.leverage
        )
        cat_a_results.append(gp)

    cat_b_results = []
    for sym, snap, tech, score, reason in cat_b_raw:
        tdata = token_data.get(sym.base_asset)
        mcap = tdata.market_cap if tdata else 0
        turnover = snap.quote_volume_24h / mcap if mcap > 0 else 0
        gp = calculate_geometric_grid(
            sym.symbol, "high_volatility", snap, tech, score, reason,
            market_cap=mcap, turnover_rate=turnover,
            leverage=cfg.leverage,
        )
        cat_b_results.append(gp)

    _step_done(5, f"共生成 {len(cat_a_results) + len(cat_b_results)} 个策略方案")
    print(f"\n  扫描完成! Category A: {len(cat_a_results)} 个 | Category B: {len(cat_b_results)} 个\n")

    return cat_a_results, cat_b_results


def format_scan_output(
    cat_a: List[GridParameters],
    cat_b: List[GridParameters],
    config=None,
) -> str:
    """
    Format the dual-category scan results for user display.
    Includes rich tables, grid strategy details, and parameter suggestions.

    v2.1 improvements:
    - Category A table now shows contract age, ATR, BB width, ADX (not volatility)
    - Category B table highlights negative funding rate opportunities
    - param_advisor receives avg_adx for accurate regime detection
    - No duplicate grid detail output
    """
    import re as _re
    try:
        from param_advisor import ParameterAdvisor, detect_market_regime
        _has_advisor = True
    except ImportError:
        _has_advisor = False

    lines = [
        f"\n{'='*70}",
        f"  \U0001f9a6 CRAYFISH GRID HUNTER v{VERSION}",
        f"  USDS-M \u6c38\u7eed\u5408\u7ea6 \u2014 \u53cc\u5206\u7c7b\u7b5b\u9009\u7ed3\u679c",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"{'='*70}",
    ]

    # --- Category A Summary Table ---
    lines.append(f"\n\U0001f4cb Category A \u2014 \u6b21\u65b0\u5e01\u6a2a\u76d8\u7c7b")
    if cat_a:
        # Header: Age(d), ATR%, BB%, ADX, Score
        lines.append(f"  {'#':<3} {'Symbol':<14} {'Price':>10} {'Age':>6} {'ATR%':>6} {'BB%':>6} {'ADX':>5} {'Score':>8}")
        lines.append(f"  {'-'*3} {'-'*14} {'-'*10} {'-'*6} {'-'*6} {'-'*6} {'-'*5} {'-'*8}")
        for i, gp in enumerate(cat_a, 1):
            # Parse age, BB width, ADX from category_reason
            age_m = _re.search(r'\u5408\u7ea6\u4e0a\u7ebf(\d+)\u5929', gp.category_reason)
            bb_m  = _re.search(r'BB\u5bbd=([\d.]+)%', gp.category_reason)
            adx_m = _re.search(r'ADX=([\d.]+)', gp.category_reason)
            age_str = f"{age_m.group(1)}d" if age_m else "?d"
            bb_str  = bb_m.group(1) if bb_m else "?"
            adx_str = adx_m.group(1) if adx_m else "?"
            # Funding highlight for negative rate
            funding_flag = " \U0001f4b0" if gp.funding_rate < 0 else ""
            lines.append(
                f"  #{i:<2} {gp.symbol:<14} "
                f"${gp.current_price:>9.4f} "
                f"{age_str:>6} "
                f"{gp.atr_pct:>5.2f}% "
                f"{bb_str:>5}% "
                f"{adx_str:>5}  "
                f"{gp.grid_score:>5.0f}/100"
                f"{funding_flag}"
            )
            lines.append(f"       \u2514\u2192 {gp.category_reason}")
    else:
        lines.append("  \u26a0\ufe0f  \u6682\u65e0\u7b26\u5408\u6761\u4ef6\u7684\u6b21\u65b0\u5e01\u6a2a\u76d8\u6807\u7684\u3002")
        lines.append("  \U0001f4a1 \u5efa\u8bae: \u5c1d\u8bd5\u8f93\u5165 '\u6b21\u65b0\u5e01\u7f51\u683c\uff0c\u5408\u7ea6\u4e0a\u7ebf\u5929\u6570\u6539\u4e3a120\u5929' \u6765\u653e\u5bbd\u7b5b\u9009\u6761\u4ef6\u3002"
        )

    # --- Category B Summary Table ---
    lines.append(f"\n\U0001f4cb Category B \u2014 \u9ad8\u6ce2\u52a8\u5957\u5229\u7c7b")
    if cat_b:
        lines.append(f"  {'#':<3} {'Symbol':<14} {'Price':>10} {'Mcap':>8} {'Turn%':>7} {'RV%':>7} {'Vol24h':>7} {'Score':>8}")
        lines.append(f"  {'-'*3} {'-'*14} {'-'*10} {'-'*8} {'-'*7} {'-'*7} {'-'*7} {'-'*8}")
        for i, gp in enumerate(cat_b, 1):
            mcap_str = f"${gp.market_cap/1e6:.0f}M" if gp.market_cap > 0 else "N/A"
            # Parse RV from reason
            rv_m = _re.search(r'RV=([\d.]+)%', gp.category_reason)
            rv_str = rv_m.group(1) if rv_m else "?"
            # Negative funding highlight
            funding_flag = " \U0001f4b0" if gp.funding_rate < 0 else ""
            lines.append(
                f"  #{i:<2} {gp.symbol:<14} "
                f"${gp.current_price:>9.4f} "
                f"{mcap_str:>8} "
                f"{gp.turnover_rate_pct:>5.0f}%  "
                f"{rv_str:>5}%  "
                f"{gp.volatility_24h_pct:>5.1f}%  "
                f"{gp.grid_score:>5.0f}/100"
                f"{funding_flag}"
            )
            lines.append(f"       \u2514\u2192 {gp.category_reason}")
        # Funding legend
        if any(gp.funding_rate < 0 for gp in cat_b):
            lines.append(f"  \U0001f4b0 = \u8d1f\u8d44\u91d1\u8d39\u7387\uff0c\u591a\u5934\u7f51\u683c\u6bcf\u65e5\u989d\u5916\u6536\u76ca")
    else:
        lines.append("  \u26a0\ufe0f  \u6682\u65e0\u7b26\u5408\u6761\u4ef6\u7684\u9ad8\u6ce2\u52a8\u5957\u5229\u6807\u7684\u3002")
        lines.append("  \U0001f4a1 \u5efa\u8bae: \u5c1d\u8bd5\u8f93\u5165 '\u9ad8\u6ce2\u52a8\u5957\u5229\uff0c\u5e02\u5024\u8303\u56f4\u653e\u5bbd\u5230\u4ebf\u523050\u4ebf\uff0c\u6362\u624b\u7387\u964d\u4f4e\u523030%' \u6765\u653e\u5bbd\u7b5b\u9009\u3002"
        )

    # --- Grid Strategy Details ---
    lines.append(f"\n{'='*70}")
    lines.append(f"  \U0001f4ca \u7b49\u6bd4\u7f51\u683c\u7b56\u7565\u8be6\u60c5")
    lines.append(f"{'='*70}")

    for gp in cat_a + cat_b:
        lines.append(gp.to_display())

    # --- Parameter Optimization Suggestions ---
    if _has_advisor:
        all_vols = [gp.volatility_24h_pct for gp in cat_a + cat_b]
        avg_vol = sum(all_vols) / len(all_vols) if all_vols else 0.0
        # Estimate avg_adx from category_reason strings
        adx_vals = []
        for gp in cat_a + cat_b:
            m = _re.search(r'ADX=([\d.]+)', gp.category_reason)
            if m:
                adx_vals.append(float(m.group(1)))
        avg_adx = sum(adx_vals) / len(adx_vals) if adx_vals else 20.0
        advisor = ParameterAdvisor()
        suggestions = advisor.analyze(
            cat_a_count=len(cat_a),
            cat_b_count=len(cat_b),
            avg_vol=avg_vol,
            avg_adx=avg_adx,
            config=config,
        )
        regime = detect_market_regime(avg_vol, avg_adx)
        lines.append(advisor.format_report(
            suggestions, regime=regime,
            cat_a_count=len(cat_a), cat_b_count=len(cat_b)
        ))

    import hashlib as _hl2
    _ts2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _sig = _hl2.md5(f"{_ts2}{VERSION}{len(cat_a)}{len(cat_b)}".encode()).hexdigest()[:12].upper()
    lines.append(f"\n{'='*70}")
    lines.append(f"  如需进一步帮助，请参阅 docs/ADVANCED.md 或在 GitHub 提交 Issue。")
    lines.append(f"  ⚠ 有效输出必含签名: CRAYFISH-{_sig} | 生成时间: {_ts2}")
    lines.append(f"{'='*70}\n")

    return "\n".join(lines)


# ============================================================
# CLI Entry Point
# ============================================================

def _build_arg_parser():
    """Build the command-line argument parser for direct script execution."""
    import argparse
    p = argparse.ArgumentParser(
        prog="grid_hunter_v5",
        description="Crayfish Grid Hunter v2.2 — USDS-M Futures Grid Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full dual-category scan with defaults
  python3 grid_hunter_v5.py

  # Category A only: recent contracts ≤90 days (default), stop-loss 8%
  python3 grid_hunter_v5.py --mode cat-a --stop-loss-pct 8.0

  # Category B only: market cap $500M-$2B, turnover ≥30%
  python3 grid_hunter_v5.py --mode cat-b --mcap-min 500000000 --mcap-max 2000000000 --turnover-min 0.30

  # Full scan, top 5 results each, no backtest
  python3 grid_hunter_v5.py --top-n 5 --no-backtest
        """,
    )

    # Scan mode
    p.add_argument(
        "--mode",
        choices=["all", "cat-a", "cat-b"],
        default="all",
        help="筛选模式: all=双分类全量, cat-a=仅次新币横盘, cat-b=仅高波动套利 (default: all)",
    )

    # Category A params
    g_a = p.add_argument_group("Category A — 次新币横盘类参数")
    g_a.add_argument("--contract-recent-days", type=int, default=None,
                     metavar="DAYS", help=f"合约上线天数上限 (default: {CONTRACT_RECENT_DAYS})")
    g_a.add_argument("--volume-shrink-ratio", type=float, default=None,
                     metavar="RATIO", help=f"量缩比率阈值 0-1 (default: {VOLUME_SHRINK_RATIO})")
    g_a.add_argument("--atr-sideways-pct", type=float, default=None,
                     metavar="PCT", help=f"ATR横盘阈值%% (default: {ATR_SIDEWAYS_PCT})")
    g_a.add_argument("--bb-width-sideways", type=float, default=None,
                     metavar="PCT", help=f"布林带宽度横盘阈值%% (default: {BB_WIDTH_SIDEWAYS})")
    g_a.add_argument("--adx-sideways", type=float, default=None,
                     metavar="VAL", help=f"ADX横盘阈值 (default: {ADX_SIDEWAYS})")

    # Category B params
    g_b = p.add_argument_group("Category B — 高波动套利类参数")
    g_b.add_argument("--mcap-min", type=float, default=None,
                     metavar="USD", help=f"市值下限 USD (default: {MCAP_MIN:.0f})")
    g_b.add_argument("--mcap-max", type=float, default=None,
                     metavar="USD", help=f"市值上限 USD (default: {MCAP_MAX:.0f})")
    g_b.add_argument("--turnover-min", type=float, default=None,
                     metavar="RATIO", help=f"换手率下限 0-1 (default: {TURNOVER_MIN})")
    g_b.add_argument("--rv-min", type=float, default=None,
                     metavar="PCT", help=f"年化RV下限%% (default: {HIGH_VOL_RV_MIN})")

    # Grid params
    g_g = p.add_argument_group("网格参数")
    g_g.add_argument("--leverage", type=int, default=None,
                     metavar="X", help=f"杠杆倍数 (default: {DEFAULT_LEVERAGE})")
    g_g.add_argument("--stop-loss-pct", type=float, default=None,
                     metavar="PCT", help="止损百分比 (default: 5.0)")
    g_g.add_argument("--min-grid-profit", type=float, default=None,
                     metavar="RATIO", help=f"最低单格利润 0-1 (default: {MIN_GRID_PROFIT})")

    # Scan control
    g_s = p.add_argument_group("扫描控制")
    g_s.add_argument("--max-symbols", type=int, default=200,
                     metavar="N", help="最多扫描的合约数量 (default: 200)")
    g_s.add_argument("--top-n", type=int, default=3,
                     metavar="N", help="每个分类返回的最佳结果数量 (default: 3)")
    g_s.add_argument("--no-backtest", action="store_true",
                     help="跳过历史回测步骤（加快速度）")
    g_s.add_argument("--no-progress", action="store_true",
                     help="不显示进度条（适合日志输出）")

    return p


def main():
    """CLI entry point for Crayfish Grid Hunter."""
    parser = _build_arg_parser()
    args = parser.parse_args()

    # Build UserConfig from CLI args
    cfg_kwargs = {}
    if args.contract_recent_days is not None:
        cfg_kwargs["contract_recent_days"] = args.contract_recent_days
    if args.volume_shrink_ratio is not None:
        cfg_kwargs["volume_shrink_ratio"] = args.volume_shrink_ratio
    if args.atr_sideways_pct is not None:
        cfg_kwargs["atr_sideways_pct"] = args.atr_sideways_pct
    if args.bb_width_sideways is not None:
        cfg_kwargs["bb_width_sideways"] = args.bb_width_sideways
    if args.adx_sideways is not None:
        cfg_kwargs["adx_sideways"] = args.adx_sideways
    if args.mcap_min is not None:
        cfg_kwargs["mcap_min"] = args.mcap_min
    if args.mcap_max is not None:
        cfg_kwargs["mcap_max"] = args.mcap_max
    if args.turnover_min is not None:
        cfg_kwargs["turnover_min"] = args.turnover_min
    if args.rv_min is not None:
        cfg_kwargs["rv_min"] = args.rv_min
    if args.leverage is not None:
        cfg_kwargs["leverage"] = args.leverage
    if args.stop_loss_pct is not None:
        cfg_kwargs["stop_loss_pct"] = args.stop_loss_pct
    if args.min_grid_profit is not None:
        cfg_kwargs["min_grid_profit"] = args.min_grid_profit
    cfg_kwargs["max_symbols"] = args.max_symbols
    cfg_kwargs["top_n"] = args.top_n

    config = UserConfig(**cfg_kwargs)

    # Validate config
    warnings = config.validate()
    if warnings:
        print("\n⚠️  参数警告:")
        for w in warnings:
            print(f"   • {w}")
        print()

    # Print config summary
    print(config.to_display())
    print()

    # Run scan
    show_progress = not args.no_progress
    cat_a, cat_b = run_dual_category_scan(
        max_symbols=config.max_symbols,
        top_n_each=config.top_n,
        config=config,
        show_progress=show_progress,
    )

    # Filter by mode
    if args.mode == "cat-a":
        cat_b = []
    elif args.mode == "cat-b":
        cat_a = []

    # Run backtest if requested
    if not args.no_backtest and (cat_a or cat_b):
        print("\n📊 正在运行历史回测...\n")
        try:
            import sys as _sys
            import os as _os
            _sys.path.insert(0, _os.path.dirname(__file__))
            from backtester import run_backtest_for_candidates
            all_candidates = cat_a + cat_b
            backtest_results = run_backtest_for_candidates(
                all_candidates,
                days=config.backtest_days,
                interval=config.backtest_interval,
            )
            for gp in all_candidates:
                bt = backtest_results.get(gp.symbol)
                if bt:
                    print(bt.format_report())
        except Exception as e:
            print(f"  ⚠️  回测模块加载失败: {e}")
            print("  💡 如需回测功能，请确保 backtester.py 在同一目录下。")

    # Format and print final output
    output = format_scan_output(cat_a, cat_b, config=config)
    print(output)


if __name__ == "__main__":
    main()
