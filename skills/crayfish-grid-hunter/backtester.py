"""
Crayfish Grid Hunter — Historical Backtester
=============================================
Simulates Geometric grid trading on historical kline data to evaluate
strategy performance before live deployment.

Features
--------
- Fetch historical klines from Binance Futures public API
- Simulate Geometric grid order fills (buy-low / sell-high)
- Track PnL, fill count, max drawdown, Sharpe ratio
- Support both Category A (sideways) and Category B (high-vol) strategies
- Generate human-readable backtest reports

Usage
-----
    from backtester import GridBacktester, BacktestConfig

    config = BacktestConfig(
        symbol="BTCUSDT",
        lower_price=60000,
        upper_price=70000,
        grid_count=30,
        leverage=5,
        initial_margin=1000,
    )
    bt = GridBacktester(config)
    result = bt.run(klines)   # klines = list of [timestamp, O, H, L, C, V]
    print(bt.format_report(result))
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

# ============================================================
# Configuration
# ============================================================

VERSION = "1.0.0"
FAPI_BASE = "https://fapi.binance.com"
MAKER_FEE = 0.0004
TAKER_FEE = 0.0005


# ============================================================
# Data Structures
# ============================================================

@dataclass
class BacktestConfig:
    """Configuration for a grid backtest run."""
    symbol: str
    lower_price: float
    upper_price: float
    grid_count: int = 30
    leverage: int = 5
    initial_margin: float = 1000.0   # USDT
    maker_fee: float = MAKER_FEE
    stop_loss_pct: float = 5.0       # % below lower bound
    grid_type: str = "geometric"     # "geometric" | "arithmetic"
    interval: str = "1h"             # Kline interval for backtest
    lookback_days: int = 30          # Days of historical data

    @property
    def stop_loss_price(self) -> float:
        return self.lower_price * (1 - self.stop_loss_pct / 100)

    @property
    def total_position(self) -> float:
        return self.initial_margin * self.leverage


@dataclass
class GridLevel:
    """A single grid level with its buy/sell state."""
    price: float
    index: int
    has_position: bool = False       # True if we bought at this level
    buy_count: int = 0
    sell_count: int = 0


@dataclass
class BacktestTrade:
    """Record of a single grid trade."""
    timestamp: int
    side: str          # "BUY" | "SELL"
    price: float
    grid_index: int
    fee: float
    pnl: float = 0.0  # Only for SELL trades


@dataclass
class BacktestResult:
    """Complete result of a backtest run."""
    config: BacktestConfig
    start_time: int
    end_time: int
    total_candles: int

    # PnL
    total_pnl: float = 0.0
    total_fees: float = 0.0
    net_pnl: float = 0.0
    roi_pct: float = 0.0

    # Trade stats
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    # Risk
    max_drawdown_pct: float = 0.0
    max_unrealized_loss_pct: float = 0.0
    stop_loss_triggered: bool = False
    stop_loss_time: Optional[int] = None

    # Performance
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    avg_profit_per_trade: float = 0.0
    fills_per_day: float = 0.0

    # Price
    price_start: float = 0.0
    price_end: float = 0.0
    price_high: float = 0.0
    price_low: float = 0.0
    time_in_range_pct: float = 0.0

    # Grid utilization
    grid_levels_touched: int = 0
    grid_utilization_pct: float = 0.0

    # History
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Tuple[int, float]] = field(default_factory=list)


# ============================================================
# Core Backtester
# ============================================================

class GridBacktester:
    """Simulates Geometric grid trading on historical kline data."""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.grid_levels: List[GridLevel] = []
        self._build_grid()

    def _build_grid(self):
        """Build geometric grid levels."""
        c = self.config
        if c.grid_type == "geometric":
            ratio = (c.upper_price / c.lower_price) ** (1 / c.grid_count)
            self.grid_levels = [
                GridLevel(
                    price=round(c.lower_price * (ratio ** i), 8),
                    index=i,
                )
                for i in range(c.grid_count + 1)
            ]
        else:
            # Arithmetic fallback
            step = (c.upper_price - c.lower_price) / c.grid_count
            self.grid_levels = [
                GridLevel(
                    price=round(c.lower_price + step * i, 8),
                    index=i,
                )
                for i in range(c.grid_count + 1)
            ]

    def run(self, klines: List[list]) -> BacktestResult:
        """
        Run backtest on historical klines.

        Parameters
        ----------
        klines : list
            Each element: [timestamp, open, high, low, close, volume, ...]
            Standard Binance kline format.

        Returns
        -------
        BacktestResult
        """
        c = self.config
        result = BacktestResult(
            config=c,
            start_time=int(klines[0][0]) if klines else 0,
            end_time=int(klines[-1][0]) if klines else 0,
            total_candles=len(klines),
            price_start=float(klines[0][4]) if klines else 0,
        )

        if not klines:
            return result

        # Position sizing: equal USDT per grid level
        usdt_per_grid = c.total_position / c.grid_count

        # Track state
        equity = c.initial_margin
        peak_equity = equity
        total_gross_profit = 0.0
        total_gross_loss = 0.0
        daily_returns: List[float] = []
        prev_equity = equity
        candles_in_range = 0

        # Reset grid
        self._build_grid()

        # Initialize: place buy orders at levels below starting price
        start_price = float(klines[0][4])
        for gl in self.grid_levels:
            if gl.price < start_price:
                gl.has_position = False  # Will buy when price touches

        for candle in klines:
            ts = int(candle[0])
            o, h, l, close = float(candle[1]), float(candle[2]), float(candle[3]), float(candle[4])

            # Check stop-loss
            if l <= c.stop_loss_price:
                result.stop_loss_triggered = True
                result.stop_loss_time = ts
                # Close all positions at stop-loss price
                for gl in self.grid_levels:
                    if gl.has_position:
                        loss = (c.stop_loss_price - gl.price) / gl.price * usdt_per_grid
                        fee = c.stop_loss_price * (usdt_per_grid / c.stop_loss_price) * c.maker_fee
                        equity += loss - fee
                        result.total_fees += fee
                        result.total_trades += 1
                        result.sell_trades += 1
                        result.losing_trades += 1
                        total_gross_loss += abs(loss)
                        gl.has_position = False
                result.equity_curve.append((ts, round(equity, 4)))
                break

            # Track price range
            result.price_high = max(result.price_high, h)
            result.price_low = min(result.price_low, l) if result.price_low > 0 else l

            if c.lower_price <= close <= c.upper_price:
                candles_in_range += 1

            # Simulate grid fills within this candle's range
            for gl in self.grid_levels:
                # BUY: price drops to this level (not already holding)
                if not gl.has_position and l <= gl.price <= h and gl.price < close:
                    fee = usdt_per_grid * c.maker_fee
                    equity -= fee
                    result.total_fees += fee
                    result.total_trades += 1
                    result.buy_trades += 1
                    gl.has_position = True
                    gl.buy_count += 1
                    result.trades.append(BacktestTrade(
                        timestamp=ts, side="BUY", price=gl.price,
                        grid_index=gl.index, fee=fee,
                    ))

                # SELL: price rises to next level (holding at this level)
                elif gl.has_position and gl.index < len(self.grid_levels) - 1:
                    next_level = self.grid_levels[gl.index + 1]
                    if l <= next_level.price <= h and next_level.price > gl.price:
                        profit = (next_level.price - gl.price) / gl.price * usdt_per_grid
                        fee = usdt_per_grid * c.maker_fee
                        net = profit - fee
                        equity += net
                        result.total_fees += fee

                        result.total_trades += 1
                        result.sell_trades += 1
                        if net > 0:
                            result.winning_trades += 1
                            total_gross_profit += net
                        else:
                            result.losing_trades += 1
                            total_gross_loss += abs(net)

                        gl.has_position = False
                        gl.sell_count += 1
                        result.trades.append(BacktestTrade(
                            timestamp=ts, side="SELL", price=next_level.price,
                            grid_index=gl.index, fee=fee, pnl=net,
                        ))

            # Track equity curve (sample every candle)
            result.equity_curve.append((ts, round(equity, 4)))

            # Max drawdown
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0
            if dd > result.max_drawdown_pct:
                result.max_drawdown_pct = dd

            # Daily return tracking (approximate: every 24 candles for 1h)
            daily_returns.append((equity - prev_equity) / max(prev_equity, 1))
            prev_equity = equity

        # Final calculations
        result.price_end = float(klines[-1][4])
        result.total_pnl = equity - c.initial_margin
        result.net_pnl = result.total_pnl
        result.roi_pct = (result.total_pnl / c.initial_margin) * 100 if c.initial_margin > 0 else 0

        if result.total_trades > 0:
            result.avg_profit_per_trade = result.net_pnl / result.total_trades

        # Time in range
        if len(klines) > 0:
            result.time_in_range_pct = candles_in_range / len(klines) * 100

        # Fills per day
        duration_days = (result.end_time - result.start_time) / (1000 * 86400) if result.end_time > result.start_time else 1
        result.fills_per_day = result.total_trades / max(duration_days, 0.01)

        # Grid utilization
        touched = sum(1 for gl in self.grid_levels if gl.buy_count > 0 or gl.sell_count > 0)
        result.grid_levels_touched = touched
        result.grid_utilization_pct = touched / len(self.grid_levels) * 100 if self.grid_levels else 0

        # Profit factor
        if total_gross_loss > 0:
            result.profit_factor = total_gross_profit / total_gross_loss
        elif total_gross_profit > 0:
            result.profit_factor = float('inf')

        # Sharpe ratio (annualized, using daily returns)
        if daily_returns and len(daily_returns) > 1:
            mean_r = sum(daily_returns) / len(daily_returns)
            var_r = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
            std_r = math.sqrt(var_r) if var_r > 0 else 0.001
            # Annualize based on interval
            periods_per_year = 365 * 24 if c.interval == "1h" else 365
            result.sharpe_ratio = (mean_r / std_r) * math.sqrt(periods_per_year)

        return result

    @staticmethod
    def format_report(result: BacktestResult) -> str:
        """Format backtest result as a human-readable report with performance rating."""
        c = result.config
        start_dt = datetime.fromtimestamp(result.start_time / 1000).strftime("%Y-%m-%d") if result.start_time else "N/A"
        end_dt = datetime.fromtimestamp(result.end_time / 1000).strftime("%Y-%m-%d") if result.end_time else "N/A"

        pnl_sign = "+" if result.net_pnl >= 0 else ""
        roi_sign = "+" if result.roi_pct >= 0 else ""

        # Performance rating
        if result.stop_loss_triggered:
            rating = "❌ 高风险 (止损触发)"
        elif result.roi_pct > 20 and result.sharpe_ratio > 2:
            rating = "🏆 优秀 (ROI>{:.0f}%, 夏普>{:.1f})".format(result.roi_pct, result.sharpe_ratio)
        elif result.roi_pct > 10:
            rating = "✅ 良好 (ROI>{:.0f}%)".format(result.roi_pct)
        elif result.roi_pct > 0:
            rating = "🟡 一般 (ROI>{:.1f}%)".format(result.roi_pct)
        else:
            rating = "🔴 亏损 (ROI{:.1f}%)".format(result.roi_pct)

        profit_factor_str = (
            f"{result.profit_factor:.2f}"
            if result.profit_factor != float('inf')
            else "∞ (无亏损交易)"
        )

        lines = [
            f"\n{'='*65}",
            f"  📊 CRAYFISH GRID HUNTER v{VERSION} — 回测报告",
            f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"{'='*65}",
            f"",
            f"  标的           : {c.symbol}  [综合评定: {rating}]",
            f"  回测周期       : {start_dt} → {end_dt} ({result.total_candles} 根K线, {c.interval})",
            f"  网格类型       : {c.grid_type.capitalize()} 等比网格 ({c.grid_count} 格)",
            f"  网格区间       : ${c.lower_price:.4f} — ${c.upper_price:.4f}",
            f"  杠杆倍数       : {c.leverage}×",
            f"  初始保证金     : ${c.initial_margin:.2f} USDT",
            f"  总仓位规模     : ${c.total_position:.2f} USDT",
            f"",
            f"  ─── 收益表现 ───",
            f"  净收益 (Net PnL)  : {pnl_sign}${result.net_pnl:.2f} USDT  ({roi_sign}{result.roi_pct:.2f}%)",
            f"  总手续费         : ${result.total_fees:.2f} USDT",
            f"  最大回撤         : {result.max_drawdown_pct:.2f}%",
            f"  夏普比率         : {result.sharpe_ratio:.2f}",
            f"  盈亏比           : {profit_factor_str}",
            f"",
            f"  ─── 交易统计 ───",
            f"  总交易次数       : {result.total_trades} 次 ({result.buy_trades} 买入 / {result.sell_trades} 卖出)",
            f"  胜率             : {result.winning_trades}/{result.sell_trades} ({result.winning_trades/max(result.sell_trades,1)*100:.1f}%)",
            f"  单笔均盈         : ${result.avg_profit_per_trade:.4f} USDT",
            f"  日均成交次数     : {result.fills_per_day:.1f} 次/天",
            f"",
            f"  ─── 市场表现 ───",
            f"  开始价格         : ${result.price_start:.4f}",
            f"  结束价格         : ${result.price_end:.4f}",
            f"  价格区间         : ${result.price_low:.4f} — ${result.price_high:.4f}",
            f"  区间内时间占比   : {result.time_in_range_pct:.1f}%",
            f"  网格利用率       : {result.grid_levels_touched}/{len(GridBacktester(c).grid_levels)} 格 ({result.grid_utilization_pct:.1f}%)",
        ]

        if result.stop_loss_triggered:
            sl_dt = datetime.fromtimestamp(result.stop_loss_time / 1000).strftime("%Y-%m-%d %H:%M") if result.stop_loss_time else "N/A"
            lines.append(f"")
            lines.append(f"  ⚠️ 止损触发       : {sl_dt}")
            lines.append(f"  💡 建议: 尝试降低杠杆倍数或放宽止损位以提高策略鲁棒性。")

        lines.append(f"\n{'='*65}")
        return "\n".join(lines)


# ============================================================
# Historical Data Fetcher
# ============================================================

def fetch_historical_klines(
    symbol: str,
    interval: str = "1h",
    lookback_days: int = 30,
    base_url: str = FAPI_BASE,
) -> List[list]:
    """
    Fetch historical klines from Binance Futures API.

    Parameters
    ----------
    symbol : str
        Trading pair (e.g. "BTCUSDT")
    interval : str
        Kline interval ("1m", "5m", "15m", "1h", "4h", "1d")
    lookback_days : int
        Number of days to look back
    base_url : str
        API base URL

    Returns
    -------
    List of klines in standard Binance format
    """
    end_time = int(time.time() * 1000)
    start_time = end_time - lookback_days * 86400 * 1000

    all_klines = []
    current_start = start_time

    while current_start < end_time:
        try:
            r = requests.get(
                f"{base_url}/fapi/v1/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": current_start,
                    "endTime": end_time,
                    "limit": 1500,
                },
                timeout=10,
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            all_klines.extend(batch)
            current_start = int(batch[-1][0]) + 1
            if len(batch) < 1500:
                break
        except Exception as e:
            print(f"  [WARN] Failed to fetch klines for {symbol}: {e}")
            break

    return all_klines


def run_backtest(
    symbol: str,
    lower_price: float,
    upper_price: float,
    grid_count: int = 30,
    leverage: int = 5,
    initial_margin: float = 1000.0,
    interval: str = "1h",
    lookback_days: int = 30,
    klines: Optional[List[list]] = None,
) -> BacktestResult:
    """
    Convenience function to run a complete backtest.

    If `klines` is None, fetches historical data from Binance Futures API.
    """
    config = BacktestConfig(
        symbol=symbol,
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=grid_count,
        leverage=leverage,
        initial_margin=initial_margin,
        interval=interval,
        lookback_days=lookback_days,
    )

    if klines is None:
        klines = fetch_historical_klines(symbol, interval, lookback_days)

    if not klines:
        print(f"  [WARN] No kline data available for {symbol}")
        return BacktestResult(config=config, start_time=0, end_time=0, total_candles=0)

    bt = GridBacktester(config)
    result = bt.run(klines)
    return result

