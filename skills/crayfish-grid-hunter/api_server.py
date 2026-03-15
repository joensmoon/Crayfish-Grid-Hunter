"""
Crayfish Grid Hunter — REST API Server & Webhook Support
=========================================================
Provides a lightweight FastAPI-based REST interface for programmatic
access to the Crayfish Grid Hunter engine.

Endpoints
---------
GET  /health              — Health check
GET  /scan                — Run full dual-category scan
GET  /scan/category-a     — Run Category A scan only
GET  /scan/category-b     — Run Category B scan only
POST /backtest            — Run backtest for a specific symbol
GET  /monitor/status      — Get current monitor status
POST /webhook/test        — Test webhook connectivity

Author: joensmoon
Version: 1.0.0
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ============================================================
# Webhook Client
# ============================================================

class WebhookClient:
    """
    Sends alert notifications to a configured webhook URL.

    Supports Telegram, Discord, Feishu, and generic HTTP POST.
    """

    def __init__(self, url: Optional[str] = None, timeout: int = 10):
        self.url = url or os.environ.get("WEBHOOK_URL", "")
        self.timeout = timeout
        self._history: List[Dict] = []

    @property
    def is_configured(self) -> bool:
        return bool(self.url)

    def send(self, level: str, symbol: str, message: str,
             value: float = 0.0, extra: Optional[Dict] = None) -> bool:
        """
        Send a webhook notification.

        Parameters
        ----------
        level : str
            Alert level: CRITICAL | HIGH | MEDIUM | INFO
        symbol : str
            Trading symbol (e.g., BTCUSDT)
        message : str
            Human-readable alert message
        value : float
            Numeric value that triggered the alert
        extra : dict
            Additional data to include in the payload

        Returns
        -------
        bool
            True if the webhook was sent successfully.
        """
        if not self.is_configured or not HAS_REQUESTS:
            return False

        payload = {
            "id": str(uuid.uuid4()),
            "level": level,
            "symbol": symbol,
            "message": message,
            "value": round(value, 6),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "crayfish-grid-hunter",
        }
        if extra:
            payload.update(extra)

        self._history.append(payload)

        try:
            resp = _requests.post(
                self.url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"  [WARN] Webhook 发送失败: {e}")
            return False

    def send_scan_result(self, cat_a_count: int, cat_b_count: int,
                         top_symbol: Optional[str] = None) -> bool:
        """Send a scan completion notification."""
        message = (
            f"扫描完成: Category A {cat_a_count} 个标的, "
            f"Category B {cat_b_count} 个标的"
        )
        if top_symbol:
            message += f"，最优推荐: {top_symbol}"
        return self.send("INFO", "SYSTEM", message)

    def send_critical_alert(self, symbol: str, alert_msg: str, value: float) -> bool:
        """Send a CRITICAL level alert."""
        return self.send("CRITICAL", symbol, alert_msg, value)

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Return recent webhook send history."""
        return self._history[-limit:]


# ============================================================
# FastAPI Application
# ============================================================

def create_api_app():
    """Create and configure the FastAPI application."""
    if not HAS_FASTAPI:
        raise ImportError(
            "FastAPI 未安装。请运行: pip install fastapi uvicorn\n"
            "注意: API 服务器是可选功能，核心 skill 功能无需此依赖。"
        )

    app = FastAPI(
        title="Crayfish Grid Hunter API",
        description=(
            "USDS-M 永续合约网格猎手 REST API。\n"
            "提供双分类筛选、历史回测和实时监控的程序化访问接口。\n"
            "Author: joensmoon | Version: 1.0.0"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # --------------------------------------------------------
    # Request/Response Models
    # --------------------------------------------------------

    class ScanConfig(BaseModel):
        contract_recent_days: int = 90
        volume_shrink_ratio: float = 0.50
        atr_sideways_pct: float = 2.0
        bb_width_sideways: float = 5.0
        adx_sideways: float = 20.0
        mcap_min: float = 200_000_000
        mcap_max: float = 1_000_000_000
        turnover_min: float = 0.50
        rv_min: float = 15.0
        leverage: int = 5
        stop_loss_pct: float = 5.0
        top_n: int = 3
        max_symbols: int = 200

    class BacktestRequest(BaseModel):
        symbol: str
        lower_price: float
        upper_price: float
        grid_count: int = 30
        leverage: int = 5
        initial_margin: float = 1000.0
        lookback_days: int = 30
        interval: str = "1h"

    class WebhookTestRequest(BaseModel):
        url: str
        message: str = "Crayfish Grid Hunter Webhook Test"

    # --------------------------------------------------------
    # Routes
    # --------------------------------------------------------

    @app.get("/health", tags=["System"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "service": "crayfish-grid-hunter",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    @app.get("/scan", tags=["Scan"])
    async def run_full_scan(
        top_n: int = Query(3, ge=1, le=10, description="每类别返回的推荐数量"),
        max_symbols: int = Query(200, ge=50, le=500, description="扫描的合约数量上限"),
        leverage: int = Query(5, ge=1, le=20, description="网格杠杆倍数"),
    ):
        """
        Run the full dual-category scan.

        Returns Category A (次新币横盘) and Category B (高波动套利) results.
        """
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(__file__))
            from grid_hunter_v5 import run_dual_category_scan, UserConfig

            config = UserConfig(top_n=top_n, max_symbols=max_symbols, leverage=leverage)
            cat_a, cat_b = run_dual_category_scan(
                max_symbols=max_symbols, top_n_each=top_n, config=config
            )

            def gp_to_dict(gp) -> Dict:
                return {
                    "symbol": gp.symbol,
                    "category": gp.category,
                    "current_price": gp.current_price,
                    "lower_price": gp.lower_price,
                    "upper_price": gp.upper_price,
                    "grid_count": gp.grid_count,
                    "grid_ratio": gp.grid_ratio,
                    "profit_per_grid_pct": gp.profit_per_grid_pct,
                    "stop_loss_price": gp.stop_loss_price,
                    "liquidation_price": gp.liquidation_price,
                    "leverage": gp.leverage,
                    "funding_rate": gp.funding_rate,
                    "volatility_24h_pct": gp.volatility_24h_pct,
                    "atr_pct": gp.atr_pct,
                    "support": gp.support,
                    "resistance": gp.resistance,
                    "grid_score": gp.grid_score,
                    "category_reason": gp.category_reason,
                    "market_cap": gp.market_cap,
                    "turnover_rate_pct": gp.turnover_rate_pct,
                }

            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "category_a": [gp_to_dict(gp) for gp in cat_a],
                "category_b": [gp_to_dict(gp) for gp in cat_b],
                "total_results": len(cat_a) + len(cat_b),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/backtest", tags=["Backtest"])
    async def run_backtest(req: BacktestRequest):
        """
        Run a historical backtest for a specific symbol and grid configuration.
        """
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(__file__))
            from backtester import GridBacktester, BacktestConfig
            from grid_hunter_v5 import fetch_klines

            config = BacktestConfig(
                symbol=req.symbol,
                lower_price=req.lower_price,
                upper_price=req.upper_price,
                grid_count=req.grid_count,
                leverage=req.leverage,
                initial_margin=req.initial_margin,
                lookback_days=req.lookback_days,
                interval=req.interval,
            )

            limit = req.lookback_days * (24 if req.interval == "1h" else 1)
            klines = fetch_klines(req.symbol, interval=req.interval, limit=limit)

            if not klines:
                raise HTTPException(status_code=404, detail=f"无法获取 {req.symbol} 的历史数据")

            bt = GridBacktester(config)
            result = bt.run(klines)

            return {
                "status": "success",
                "symbol": req.symbol,
                "roi_pct": result.roi_pct,
                "sharpe_ratio": result.sharpe_ratio,
                "max_drawdown_pct": result.max_drawdown_pct,
                "total_trades": result.total_trades,
                "fills_per_day": result.fills_per_day,
                "stop_loss_triggered": result.stop_loss_triggered,
                "net_pnl": result.net_pnl,
                "total_fees": result.total_fees,
                "time_in_range_pct": result.time_in_range_pct,
                "grid_utilization_pct": result.grid_utilization_pct,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/webhook/test", tags=["Webhook"])
    async def test_webhook(req: WebhookTestRequest):
        """Test webhook connectivity by sending a test notification."""
        client = WebhookClient(url=req.url)
        success = client.send(
            level="INFO",
            symbol="TEST",
            message=req.message,
            extra={"test": True},
        )
        return {
            "status": "sent" if success else "failed",
            "url": req.url,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return app


def start_api_server(host: str = "0.0.0.0", port: int = 8765):
    """Start the API server."""
    if not HAS_FASTAPI:
        print("❌ FastAPI 未安装。请运行: pip install fastapi uvicorn")
        return
    app = create_api_app()
    print(f"🚀 Crayfish Grid Hunter API 服务已启动: http://{host}:{port}")
    print(f"📖 API 文档: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_api_server()

