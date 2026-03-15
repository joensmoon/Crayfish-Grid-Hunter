"""
Crayfish Grid Hunter — Parameter Optimization Advisor
======================================================
Analyzes scan results and market conditions to provide
data-driven parameter optimization suggestions.

Author: joensmoon
Version: 2.0.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============================================================
# Market Regime Detection
# ============================================================

class MarketRegime:
    """Classify the current market regime based on volatility and trend."""
    SIDEWAYS   = "SIDEWAYS"    # Low volatility, no clear trend
    TRENDING   = "TRENDING"    # Strong directional movement
    VOLATILE   = "VOLATILE"    # High volatility, chaotic
    BREAKOUT   = "BREAKOUT"    # Volatility expanding rapidly


def detect_market_regime(
    avg_volatility_24h: float,
    avg_adx: float,
    vol_change_pct: float = 0.0,
) -> str:
    """
    Detect market regime from aggregated market statistics.

    Parameters
    ----------
    avg_volatility_24h : float
        Average 24h intraday volatility across scanned symbols.
    avg_adx : float
        Average ADX(14) across scanned symbols.
    vol_change_pct : float
        Percentage change in average volatility vs previous period.

    Returns
    -------
    str
        One of MarketRegime constants.
    """
    if vol_change_pct > 50:
        return MarketRegime.BREAKOUT
    if avg_volatility_24h > 15 and avg_adx > 25:
        return MarketRegime.VOLATILE
    if avg_adx > 25:
        return MarketRegime.TRENDING
    return MarketRegime.SIDEWAYS


# ============================================================
# Suggestion Data Structure
# ============================================================

@dataclass
class ParamSuggestion:
    """A single parameter optimization suggestion."""
    param_name: str
    current_value: float
    suggested_value: float
    reason: str
    priority: str = "MEDIUM"   # HIGH | MEDIUM | LOW
    impact: str = ""

    def to_display(self) -> str:
        direction = "↑" if self.suggested_value > self.current_value else "↓"
        return (
            f"  [{self.priority}] {self.param_name}: "
            f"{self.current_value} → {self.suggested_value} {direction}\n"
            f"    原因: {self.reason}\n"
            f"    预期效果: {self.impact}"
        )


# ============================================================
# Parameter Advisor Engine
# ============================================================

class ParameterAdvisor:
    """
    Analyzes scan results and market conditions to suggest
    optimal parameter adjustments.

    Usage
    -----
    advisor = ParameterAdvisor()
    suggestions = advisor.analyze(
        cat_a_count=0,
        cat_b_count=2,
        avg_vol=18.5,
        avg_adx=22.0,
        config=current_config,
    )
    print(advisor.format_report(suggestions))
    """

    def analyze(
        self,
        cat_a_count: int,
        cat_b_count: int,
        avg_vol: float = 10.0,
        avg_adx: float = 20.0,
        vol_change_pct: float = 0.0,
        config=None,
    ) -> List[ParamSuggestion]:
        """
        Generate parameter suggestions based on results and market regime.

        Parameters
        ----------
        cat_a_count : int
            Number of Category A results found.
        cat_b_count : int
            Number of Category B results found.
        avg_vol : float
            Average 24h volatility of scanned symbols.
        avg_adx : float
            Average ADX across scanned symbols.
        vol_change_pct : float
            Volatility change vs previous period.
        config : UserConfig, optional
            Current configuration instance.

        Returns
        -------
        List[ParamSuggestion]
            Ordered list of suggestions (highest priority first).
        """
        suggestions: List[ParamSuggestion] = []
        regime = detect_market_regime(avg_vol, avg_adx, vol_change_pct)

        # --- Category A suggestions ---
        if cat_a_count == 0:
            suggestions.append(ParamSuggestion(
                param_name="contract_recent_days",
                current_value=getattr(config, "contract_recent_days", 90),
                suggested_value=120,
                reason="次新币筛选无结果，当前上线天数阈值过严",
                priority="HIGH",
                impact="扩大候选池，预计增加 30-50% 的候选标的",
            ))
            suggestions.append(ParamSuggestion(
                param_name="volume_shrink_ratio",
                current_value=getattr(config, "volume_shrink_ratio", 0.50),
                suggested_value=0.70,
                reason="成交量萎缩要求过严，可适当放宽",
                priority="MEDIUM",
                impact="允许更多轻微缩量的标的通过筛选",
            ))

        elif cat_a_count >= 5:
            suggestions.append(ParamSuggestion(
                param_name="contract_recent_days",
                current_value=getattr(config, "contract_recent_days", 90),
                suggested_value=60,
                reason="次新币候选过多，收紧以提高精度",
                priority="LOW",
                impact="减少候选数量，聚焦更新的合约",
            ))

        # --- Category B suggestions ---
        if cat_b_count == 0:
            suggestions.append(ParamSuggestion(
                param_name="mcap_min",
                current_value=getattr(config, "mcap_min", 200_000_000),
                suggested_value=100_000_000,
                reason="高波动筛选无结果，市值下限过高",
                priority="HIGH",
                impact="将市值下限降至 1亿，扩大候选范围",
            ))
            suggestions.append(ParamSuggestion(
                param_name="turnover_min",
                current_value=getattr(config, "turnover_min", 0.50),
                suggested_value=0.30,
                reason="换手率要求过高，当前市场活跃度不足",
                priority="HIGH",
                impact="降低换手率门槛，预计增加 50% 的候选标的",
            ))

        # --- Regime-based grid parameter suggestions ---
        # High volatility check: trigger on avg_vol > 15% regardless of ADX
        if avg_vol > 15 or regime == MarketRegime.VOLATILE:
            current_lev = getattr(config, "leverage", 5)
            if current_lev > 3:
                suggestions.append(ParamSuggestion(
                    param_name="leverage",
                    current_value=current_lev,
                    suggested_value=3,
                    reason=f"当前市场高波动（平均 {avg_vol:.1f}%），高杠杆风险极大",
                    priority="HIGH",
                    impact="降低杠杆可减少强平风险，保护本金",
                ))
            current_sl = getattr(config, "stop_loss_pct", 5.0)
            if current_sl < 8:
                suggestions.append(ParamSuggestion(
                    param_name="stop_loss_pct",
                    current_value=current_sl,
                    suggested_value=8.0,
                    reason=f"高波动市场（{avg_vol:.1f}%）下止损过窄，易频繁触发",
                    priority="HIGH",
                    impact="放宽止损位可减少不必要的止损，提高策略持续性",
                ))

        if regime == MarketRegime.SIDEWAYS and avg_vol <= 15:
            current_profit = getattr(config, "min_grid_profit", 0.008)
            if current_profit > 0.01:
                suggestions.append(ParamSuggestion(
                    param_name="min_grid_profit",
                    current_value=current_profit * 100,
                    suggested_value=0.8,
                    reason="横盘市场适合密集网格，可适当降低单格利润要求",
                    priority="LOW",
                    impact="增加网格密度，提高成交频率",
                ))

        elif regime == MarketRegime.BREAKOUT:
            suggestions.append(ParamSuggestion(
                param_name="leverage",
                current_value=getattr(config, "leverage", 5),
                suggested_value=2,
                reason="检测到波动率急剧扩大（突破行情），建议大幅降低杠杆",
                priority="HIGH",
                impact="保护本金，避免在突破行情中被强平",
            ))

        # Sort by priority
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))

        return suggestions

    def format_report(
        self,
        suggestions: List[ParamSuggestion],
        regime: str = "",
        cat_a_count: int = 0,
        cat_b_count: int = 0,
    ) -> str:
        """Format suggestions as a readable report."""
        lines = [
            "\n" + "="*60,
            "  🔧 参数优化建议报告",
            "="*60,
        ]

        if regime:
            regime_emoji = {
                MarketRegime.SIDEWAYS: "😴 横盘震荡",
                MarketRegime.TRENDING: "📈 趋势行情",
                MarketRegime.VOLATILE: "🌪️ 高波动",
                MarketRegime.BREAKOUT: "💥 突破行情",
            }
            lines.append(f"\n  当前市场状态: {regime_emoji.get(regime, regime)}")

        lines.append(f"  筛选结果: Category A {cat_a_count} 个 | Category B {cat_b_count} 个")

        if not suggestions:
            lines.append("\n  ✅ 当前参数配置合理，无需调整。")
        else:
            lines.append(f"\n  共 {len(suggestions)} 条优化建议:\n")
            for i, s in enumerate(suggestions, 1):
                lines.append(f"  [{i}] {s.to_display()}")

        lines.append("="*60)
        return "\n".join(lines)
