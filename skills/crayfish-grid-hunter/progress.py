"""
Crayfish Grid Hunter — Progress & Display Utilities
====================================================
Provides progress bars, rich table formatting, and user-friendly
error messages for the OpenClaw agent environment.

Author: joensmoon
Version: 1.0.0
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================================
# ANSI Color Codes (for terminal output)
# ============================================================
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"


def _supports_color() -> bool:
    """Check if the terminal supports ANSI color codes."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def colorize(text: str, color: str) -> str:
    """Apply color if terminal supports it."""
    if _supports_color():
        return f"{color}{text}{Color.RESET}"
    return text


# ============================================================
# Progress Bar
# ============================================================

class ProgressBar:
    """
    A simple, non-blocking progress bar for the agent loop.

    Usage:
        bar = ProgressBar(total=200, prefix="扫描合约")
        for i, symbol in enumerate(symbols):
            bar.update(i + 1, suffix=symbol)
        bar.finish()
    """

    def __init__(self, total: int, prefix: str = "", width: int = 40):
        self.total = max(total, 1)
        self.prefix = prefix
        self.width = width
        self._start = time.time()
        self._last_print = 0.0

    def update(self, current: int, suffix: str = ""):
        """Update the progress bar. Throttled to avoid excessive output."""
        now = time.time()
        if now - self._last_print < 0.5 and current < self.total:
            return
        self._last_print = now

        pct = current / self.total
        filled = int(self.width * pct)
        bar = "█" * filled + "░" * (self.width - filled)
        elapsed = now - self._start
        eta = (elapsed / pct - elapsed) if pct > 0.01 else 0

        line = (
            f"\r{self.prefix} [{bar}] "
            f"{current}/{self.total} ({pct*100:.0f}%) "
            f"ETA:{eta:.0f}s  {suffix[:30]:<30}"
        )
        sys.stdout.write(line)
        sys.stdout.flush()

    def finish(self, message: str = "完成"):
        """Print completion message."""
        elapsed = time.time() - self._start
        sys.stdout.write(
            f"\r{self.prefix} [{'█' * self.width}] "
            f"{self.total}/{self.total} (100%) "
            f"耗时:{elapsed:.1f}s  {message:<30}\n"
        )
        sys.stdout.flush()


class StepProgress:
    """
    Multi-step progress tracker for the full scan pipeline.

    Usage:
        sp = StepProgress(steps=["扫描", "回测", "输出"])
        sp.start_step(0)
        # ... do work ...
        sp.complete_step(0)
    """

    def __init__(self, steps: List[str]):
        self.steps = steps
        self.total = len(steps)
        self._completed: List[bool] = [False] * self.total
        self._start_times: Dict[int, float] = {}

    def start_step(self, idx: int, detail: str = ""):
        """Mark a step as started."""
        self._start_times[idx] = time.time()
        status_line = self._render(idx, "running", detail)
        print(status_line)

    def complete_step(self, idx: int, detail: str = ""):
        """Mark a step as completed."""
        self._completed[idx] = True
        elapsed = time.time() - self._start_times.get(idx, time.time())
        status_line = self._render(idx, "done", f"{detail} ({elapsed:.1f}s)")
        print(status_line)

    def fail_step(self, idx: int, error: str = ""):
        """Mark a step as failed."""
        status_line = self._render(idx, "fail", error)
        print(status_line)

    def _render(self, idx: int, state: str, detail: str) -> str:
        icons = {"running": "⏳", "done": "✅", "fail": "❌"}
        icon = icons.get(state, "•")
        step_name = self.steps[idx] if idx < len(self.steps) else f"Step {idx}"
        return f"  {icon} [{idx+1}/{self.total}] {step_name}  {detail}"


# ============================================================
# Rich Table Formatter
# ============================================================

def format_table(headers: List[str], rows: List[List[Any]],
                 title: str = "", align: Optional[List[str]] = None) -> str:
    """
    Format data as a clean ASCII table.

    Parameters
    ----------
    headers : List[str]
        Column header names.
    rows : List[List[Any]]
        Table data rows.
    title : str
        Optional table title.
    align : List[str]
        Alignment per column: 'l' (left), 'r' (right), 'c' (center).
        Defaults to left for all.
    """
    if not rows:
        return f"  (暂无数据)\n"

    all_rows = [[str(h) for h in headers]] + [[str(c) for c in row] for row in rows]
    col_widths = [max(len(r[i]) for r in all_rows) for i in range(len(headers))]

    if align is None:
        align = ["l"] * len(headers)

    def _cell(text: str, width: int, a: str) -> str:
        if a == "r":
            return text.rjust(width)
        elif a == "c":
            return text.center(width)
        return text.ljust(width)

    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = "|" + "|".join(
        f" {_cell(h, col_widths[i], 'c')} " for i, h in enumerate(headers)
    ) + "|"

    lines = []
    if title:
        total_width = sum(w + 3 for w in col_widths) + 1
        lines.append("+" + "-" * (total_width - 2) + "+")
        lines.append("|" + title.center(total_width - 2) + "|")

    lines.append(sep)
    lines.append(header_row)
    lines.append(sep)

    for row in rows:
        data_row = "|" + "|".join(
            f" {_cell(str(row[i]), col_widths[i], align[i] if i < len(align) else 'l')} "
            for i in range(len(headers))
        ) + "|"
        lines.append(data_row)

    lines.append(sep)
    return "\n".join(lines)


# ============================================================
# User-Friendly Error Messages
# ============================================================

ERROR_SOLUTIONS: Dict[str, Dict[str, str]] = {
    "451": {
        "title": "API 地区限制 (HTTP 451)",
        "cause": "币安合约 API 在您所在地区受到访问限制。",
        "solution": (
            "系统已自动切换至测试网备用节点 (testnet.binancefuture.com)。\n"
            "  如果问题持续，请检查您的网络环境或使用代理。"
        ),
    },
    "timeout": {
        "title": "请求超时",
        "cause": "网络延迟过高，API 请求未能在规定时间内响应。",
        "solution": (
            "请检查您的网络连接。\n"
            "  系统将自动重试，或您可以稍后再次尝试。"
        ),
    },
    "no_results_a": {
        "title": "Category A 无筛选结果",
        "cause": "当前市场没有符合次新币横盘条件的合约。",
        "solution": (
            "可以尝试放宽参数，例如：\n"
            "  '次新币网格，合约上线天数改为120天，ATR放宽到3%'"
        ),
    },
    "no_results_b": {
        "title": "Category B 无筛选结果",
        "cause": "当前市场没有符合高波动套利条件的合约。",
        "solution": (
            "可以尝试放宽参数，例如：\n"
            "  '高波动套利，市值范围放宽到1亿到50亿，换手率降低到30%'"
        ),
    },
    "api_key_missing": {
        "title": "API 密钥未配置",
        "cause": "账户余额检查和费用优化功能需要币安 API 密钥。",
        "solution": (
            "核心筛选和回测功能无需 API 密钥，可继续使用。\n"
            "  如需完整功能，请设置环境变量：\n"
            "  export BINANCE_API_KEY='your_key'\n"
            "  export BINANCE_API_SECRET='your_secret'"
        ),
    },
    "token_info_empty": {
        "title": "市值数据获取失败",
        "cause": "query-token-info 接口返回空数据，可能是频率限制或网络问题。",
        "solution": (
            "Category B 筛选需要市值数据。请稍后重试。\n"
            "  如果持续失败，可以使用 Category A（次新币网格）作为替代。"
        ),
    },
}


def format_error(error_key: str, extra: str = "") -> str:
    """Format a user-friendly error message."""
    info = ERROR_SOLUTIONS.get(error_key, {
        "title": "未知错误",
        "cause": extra or "发生了未知错误。",
        "solution": "请检查日志并重试，或在 GitHub 提交 Issue。",
    })
    lines = [
        f"\n{'⚠️ ' + info['title']:}",
        f"  原因: {info['cause']}",
        f"  解决: {info['solution']}",
    ]
    if extra and error_key in ERROR_SOLUTIONS:
        lines.append(f"  详情: {extra}")
    return "\n".join(lines)


def format_warning(message: str) -> str:
    """Format a warning message."""
    return f"  ⚠️  {message}"


def format_success(message: str) -> str:
    """Format a success message."""
    return f"  ✅ {message}"


def format_info(message: str) -> str:
    """Format an info message."""
    return f"  ℹ️  {message}"


# ============================================================
# Parameter Optimization Advisor
# ============================================================

def generate_param_suggestions(
    cat_a_count: int,
    cat_b_count: int,
    market_vol_avg: float = 0.0,
    config_dict: Optional[Dict] = None,
) -> str:
    """
    Generate parameter optimization suggestions based on screening results.

    Parameters
    ----------
    cat_a_count : int
        Number of Category A results found.
    cat_b_count : int
        Number of Category B results found.
    market_vol_avg : float
        Average 24h volatility of scanned symbols.
    config_dict : dict
        Current UserConfig as a dictionary.

    Returns
    -------
    str
        Formatted suggestions string.
    """
    suggestions = []

    if cat_a_count == 0:
        suggestions.append(
            "📊 次新币筛选无结果：建议将 contract_recent_days 从 90 天放宽至 120 天，"
            "或将 volume_shrink_ratio 从 50% 放宽至 70%。"
        )
    elif cat_a_count >= 5:
        suggestions.append(
            "📊 次新币候选较多：建议将 contract_recent_days 收紧至 60 天，"
            "或将 atr_sideways_pct 从 2% 收紧至 1.5%，以提高筛选精度。"
        )

    if cat_b_count == 0:
        suggestions.append(
            "📊 高波动筛选无结果：建议将市值范围扩大（mcap_min 降至 1亿，mcap_max 升至 50亿），"
            "或将 turnover_min 从 50% 降低至 30%。"
        )

    if market_vol_avg > 20:
        suggestions.append(
            "📈 当前市场整体波动较高（平均 24h 波动 >20%）：建议适当降低杠杆（如 3x），"
            "并将止损位放宽至 8%，以避免频繁触发止损。"
        )
    elif market_vol_avg < 5 and market_vol_avg > 0:
        suggestions.append(
            "📉 当前市场整体波动较低（平均 24h 波动 <5%）：适合次新币横盘策略，"
            "建议将 grid_count 减少至 20，以确保单格利润空间。"
        )

    if not suggestions:
        suggestions.append("✅ 当前参数配置合理，筛选结果质量良好。")

    lines = ["\n【参数优化建议】"]
    for i, s in enumerate(suggestions, 1):
        lines.append(f"  {i}. {s}")
    return "\n".join(lines)


# ============================================================
# Backtest Summary Formatter
# ============================================================

def format_backtest_summary(results: List[Dict]) -> str:
    """
    Format multiple backtest results as a comparison table.

    Parameters
    ----------
    results : List[Dict]
        Each dict should have: symbol, roi_pct, sharpe, max_drawdown_pct,
        total_trades, fills_per_day, stop_loss_triggered.
    """
    if not results:
        return "  (无回测结果)\n"

    headers = ["标的", "ROI%", "夏普比率", "最大回撤%", "总交易次数", "日均成交", "止损触发"]
    rows = []
    for r in results:
        sl = "是 ⚠️" if r.get("stop_loss_triggered") else "否 ✅"
        rows.append([
            r.get("symbol", "N/A"),
            f"{r.get('roi_pct', 0):.2f}%",
            f"{r.get('sharpe', 0):.2f}",
            f"{r.get('max_drawdown_pct', 0):.2f}%",
            str(r.get("total_trades", 0)),
            f"{r.get('fills_per_day', 0):.1f}",
            sl,
        ])

    return format_table(
        headers, rows,
        title="30天历史回测对比",
        align=["l", "r", "r", "r", "r", "r", "c"],
    )


# ============================================================
# Scan Results Formatter (Enhanced)
# ============================================================

def format_scan_results_table(cat_a_results: List[Dict], cat_b_results: List[Dict]) -> str:
    """
    Format scan results as rich tables for both categories.
    """
    lines = [
        f"\n{'='*70}",
        f"  🦐 CRAYFISH GRID HUNTER — 双分类筛选结果",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"{'='*70}",
    ]

    # Category A Table
    lines.append("\n📋 Category A — 次新币横盘类")
    if cat_a_results:
        headers_a = ["排名", "标的", "当前价", "上线天数", "ATR%", "BB宽%", "ADX", "评分"]
        rows_a = []
        for i, r in enumerate(cat_a_results, 1):
            rows_a.append([
                f"#{i}",
                r.get("symbol", ""),
                f"${r.get('current_price', 0):.4f}",
                f"{r.get('contract_age_days', 0):.0f}天",
                f"{r.get('atr_pct', 0):.2f}%",
                f"{r.get('bb_width_pct', 0):.2f}%",
                f"{r.get('adx', 0):.1f}",
                f"{r.get('score', 0):.0f}/100",
            ])
        lines.append(format_table(headers_a, rows_a, align=["c", "l", "r", "r", "r", "r", "r", "r"]))
    else:
        lines.append(format_error("no_results_a"))

    # Category B Table
    lines.append("\n📋 Category B — 高波动套利类")
    if cat_b_results:
        headers_b = ["排名", "标的", "当前价", "市值(M)", "换手率%", "RV%/yr", "24h波动%", "评分"]
        rows_b = []
        for i, r in enumerate(cat_b_results, 1):
            rows_b.append([
                f"#{i}",
                r.get("symbol", ""),
                f"${r.get('current_price', 0):.4f}",
                f"${r.get('market_cap', 0)/1e6:.0f}M",
                f"{r.get('turnover_rate_pct', 0):.0f}%",
                f"{r.get('rv_pct', 0):.1f}%",
                f"{r.get('volatility_24h_pct', 0):.1f}%",
                f"{r.get('score', 0):.0f}/100",
            ])
        lines.append(format_table(headers_b, rows_b, align=["c", "l", "r", "r", "r", "r", "r", "r"]))
    else:
        lines.append(format_error("no_results_b"))

    return "\n".join(lines)
