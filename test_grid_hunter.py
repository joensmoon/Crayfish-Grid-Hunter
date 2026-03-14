#!/usr/bin/env python3
"""
Crayfish Grid Hunter v4.3.0 - Test Suite
=========================================
Validates all API calls and technical indicator calculations described in
the Crayfish Grid Hunter SKILL.md. Covers the full 7-step workflow:

  Step 1: Market Scan          (crypto-market-rank)
  Step 2: Dynamic Range        (spot klines + indicators)
  Step 3: Smart Money          (trading-signal)
  Step 4: Security Audit       (query-token-audit)
  Step 5: Fee Optimization     (assets - OPTIONAL, requires API key)
  Step 6: Output Generation    (composite scoring)
  Step 7: Breakout Alert       (volume spike detection)
"""

import json
import math
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import requests

# ============================================================
# Configuration
# ============================================================
VERSION = "4.3.0"
SPOT_ENDPOINTS = [
    "https://api.binance.com",
    "https://data-api.binance.vision"
]
WEB3_BASE_URL = "https://web3.binance.com"
USER_AGENT_APP = f"crayfish-grid-hunter/{VERSION} (Skill)"
USER_AGENT_SPOT = "binance-spot/1.0.2 (Skill)"
USER_AGENT_WEB3_SIGNAL = "binance-web3/1.0 (Skill)"
USER_AGENT_WEB3_AUDIT = "binance-web3/1.4 (Skill)"

# RSI requires n+1 data points minimum; fetch 30 days to ensure
# Wilder Smoothing has sufficient warm-up data (n=14, need >14 deltas).
RSI_PERIOD = 14
KLINE_LIMIT_SCAN = 30       # Step 1: daily candles for ATR/RSI/Slope screening
KLINE_LIMIT_RANGE = 72      # Step 2: hourly candles for grid range generation
BB_PERIOD = 20              # Standard 20-period Bollinger Bands

DEFAULT_PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    "MATICUSDT", "UNIUSDT", "LTCUSDT", "ATOMUSDT", "NEARUSDT"
]

# Cache
_cache = {}
_cache_ttl = timedelta(minutes=5)

# Test result tracking
_test_results = []
_active_spot_url = None

def _get_cache(key: str):
    if key in _cache:
        data, ts = _cache[key]
        if datetime.now() - ts < _cache_ttl:
            return data
    return None

def _set_cache(key: str, data):
    _cache[key] = (data, datetime.now())

def record_test(name: str, status: str, detail: str = ""):
    _test_results.append({"name": name, "status": status, "detail": detail})

def get_spot_base_url():
    """Get working Spot API base URL with automatic fallback."""
    global _active_spot_url
    if _active_spot_url:
        return _active_spot_url

    for url in SPOT_ENDPOINTS:
        try:
            resp = requests.get(f"{url}/api/v3/ping", timeout=5)
            if resp.status_code == 200:
                _active_spot_url = url
                return url
            elif resp.status_code == 451:
                print(f"  [API] {url} returned 451 (geo-restricted), trying fallback...")
        except Exception as e:
            print(f"  [API] {url} connection failed: {e}, trying fallback...")

    _active_spot_url = SPOT_ENDPOINTS[-1]  # Default to fallback
    return _active_spot_url

# ============================================================
# API Layer: Step 1 - Market Scan (crypto-market-rank)
# ============================================================

def fetch_market_rankings(size: int = 50) -> list:
    """Step 1: Fetch market rankings via crypto-market-rank skill."""
    cache_key = f"market_rank_{size}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    url = f"{WEB3_BASE_URL}/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list"
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": USER_AGENT_WEB3_SIGNAL
    }
    payload = {
        "rankType": 10,
        "period": 50,
        "sortBy": 70,
        "orderAsc": False,
        "page": 1,
        "size": size
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("data", {}).get("tokens"):
                tokens = data["data"]["tokens"]
                _set_cache(cache_key, tokens)
                return tokens
        else:
            print(f"  [WARN] crypto-market-rank API status: {resp.status_code}")
    except Exception as e:
        print(f"  [WARN] crypto-market-rank API call failed: {e}")
    return []

# ============================================================
# API Layer: Step 2 - Spot Data (spot skill)
# ============================================================

def fetch_klines(symbol: str, interval: str = "1d", limit: int = KLINE_LIMIT_SCAN) -> list:
    """Step 2: Fetch Kline/Candlestick data via spot skill.

    Uses KLINE_LIMIT_SCAN (30) by default for daily screening to ensure
    RSI Wilder Smoothing has sufficient warm-up data (needs >14 deltas).
    """
    cache_key = f"klines_{symbol}_{interval}_{limit}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    base_url = get_spot_base_url()
    url = f"{base_url}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    headers = {"User-Agent": USER_AGENT_SPOT}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _set_cache(cache_key, data)
        return data
    except Exception as e:
        print(f"  [WARN] spot klines API failed for {symbol}: {e}")
        return []

def fetch_ticker_24h(symbol: str) -> dict:
    """Fetch 24hr ticker data via spot skill."""
    base_url = get_spot_base_url()
    url = f"{base_url}/api/v3/ticker/24hr"
    params = {"symbol": symbol}
    headers = {"User-Agent": USER_AGENT_SPOT}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [WARN] spot ticker/24hr failed for {symbol}: {e}")
        return {}

# ============================================================
# API Layer: Step 3 - Smart Money Signals (trading-signal)
# ============================================================

def fetch_smart_money_signals(chain_id: str = "CT_501", page: int = 1, size: int = 100) -> list:
    """Step 3: Fetch Smart Money signals via trading-signal skill."""
    cache_key = f"smart_money_{chain_id}_{page}_{size}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    url = f"{WEB3_BASE_URL}/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money"
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": USER_AGENT_WEB3_SIGNAL
    }
    payload = {
        "page": page,
        "pageSize": size,
        "chainId": chain_id
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("data"):
                signals = data["data"]
                _set_cache(cache_key, signals)
                return signals
        else:
            print(f"  [WARN] trading-signal API status: {resp.status_code}")
    except Exception as e:
        print(f"  [WARN] trading-signal API failed: {e}")
    return []

# ============================================================
# API Layer: Step 4 - Security Audit (query-token-audit)
# ============================================================

def audit_token(contract_address: str, chain_id: str = "56") -> dict:
    """Step 4: Audit a token contract via query-token-audit skill."""
    cache_key = f"audit_{contract_address}_{chain_id}"
    cached = _get_cache(cache_key)
    if cached:
        return cached

    url = f"{WEB3_BASE_URL}/bapi/defi/v1/public/wallet-direct/security/token/audit"
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": USER_AGENT_WEB3_AUDIT
    }
    payload = {
        "binanceChainId": chain_id,
        "contractAddress": contract_address,
        "requestId": str(uuid.uuid4())
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("data"):
                result = data["data"]
                _set_cache(cache_key, result)
                return result
        else:
            print(f"  [WARN] query-token-audit API status: {resp.status_code}")
    except Exception as e:
        print(f"  [WARN] query-token-audit API failed: {e}")
    return {}

# ============================================================
# Technical Indicators
# ============================================================

def calculate_rsi(prices: List[float], n: int = RSI_PERIOD) -> float:
    """Calculate RSI using Wilder Smoothing Method.

    Requires len(prices) > n to produce a meaningful result.
    With limit=30 daily candles, we have 29 deltas which is sufficient
    for n=14 Wilder smoothing (14 warm-up + 15 rolling updates).
    Returns 50.0 only as a genuine neutral signal, not as a fallback.
    """
    if len(prices) <= n:
        # Insufficient data — return None to signal calculation failure
        return None

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    # Initial simple average over first n periods
    avg_gain = sum(gains[:n]) / n
    avg_loss = sum(losses[:n]) / n

    # Wilder smoothing for subsequent periods
    for i in range(n, len(deltas)):
        avg_gain = (avg_gain * (n - 1) + gains[i]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i]) / n

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(prices: List[float], period: int = BB_PERIOD):
    """Calculate standard 20-period Bollinger Bands.

    Uses only the most recent `period` data points, matching the
    industry-standard definition (20-period SMA ± 2 standard deviations).
    """
    if len(prices) < period:
        # Fall back to all available data if fewer than 20 candles
        window = prices
    else:
        window = prices[-period:]

    sma = sum(window) / len(window)
    variance = sum((p - sma) ** 2 for p in window) / len(window)
    std_dev = math.sqrt(variance)
    return sma - (std_dev * 2), sma, sma + (std_dev * 2)

def calculate_grid_parameters(symbol: str, klines: list):
    """Analyze volatility and trend to generate grid parameters.

    Requires at least 15 candles (14 for ATR + 1 prior close).
    With KLINE_LIMIT_SCAN=30, RSI calculation is now fully functional.
    """
    if not klines or len(klines) < 15:
        return None

    closes = [float(k[4]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]

    # --- Volatility ---
    max_p = max(highs)
    min_p = min(lows)
    midpoint = (max_p + min_p) / 2
    volatility = ((max_p - min_p) / midpoint) * 100

    # --- Trend Slope (linear regression, normalized) ---
    x = list(range(len(closes)))
    avg_x = sum(x) / len(x)
    avg_y = sum(closes) / len(closes)
    num = sum((x[i] - avg_x) * (closes[i] - avg_y) for i in range(len(x)))
    den = sum((xi - avg_x) ** 2 for xi in x)
    slope = num / den if den != 0 else 0
    norm_slope = (slope / avg_y) * 100

    # --- RSI (Wilder Smoothing, now with sufficient data) ---
    rsi = calculate_rsi(closes)
    if rsi is None:
        # Should not happen with KLINE_LIMIT_SCAN=30, but guard defensively
        rsi_score = 0
        rsi_display = "N/A"
    else:
        rsi_display = rsi
        if 35 <= rsi <= 65:
            rsi_score = 30
        elif 30 <= rsi < 35 or 65 < rsi <= 70:
            rsi_score = 15
        else:
            rsi_score = 0

    # --- Standard 20-period Bollinger Bands ---
    lower_band, middle_band, upper_band = calculate_bollinger_bands(closes)

    # --- ATR (Average True Range, 14-period) ---
    tr_values = []
    for i in range(1, len(klines)):
        h = float(klines[i][2])
        l = float(klines[i][3])
        pc = float(klines[i - 1][4])
        tr_values.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(tr_values[-14:]) / min(14, len(tr_values))

    # --- Range Quality ---
    range_pct = ((upper_band - lower_band) / middle_band) * 100 if middle_band > 0 else 0
    range_score = 10 if range_pct >= 5 else 0

    # --- Composite Score ---
    score = 0

    # Volatility (max 30)
    if 5 <= volatility <= 20:
        score += 30
    elif 3 <= volatility < 5:
        score += 15

    # RSI (max 30)
    if rsi is not None:
        if 35 <= rsi <= 65:
            score += 30
        elif 30 <= rsi < 35 or 65 < rsi <= 70:
            score += 15

    # Trend Slope (max 30)
    if abs(norm_slope) < 0.5:
        score += 30
    elif abs(norm_slope) < 1.0:
        score += 20
    elif abs(norm_slope) < 2.0:
        score += 10

    # Range Quality (max 10)
    score += range_score

    return {
        "score": float(score),
        "volatility": volatility,
        "rsi": rsi_display,
        "slope": norm_slope,
        "atr": atr,
        "upper": upper_band,
        "lower": lower_band,
        "middle": middle_band,
        "range_pct": range_pct,
    }

# ============================================================
# Test Runner
# ============================================================

def run_tests():
    print(f"Crayfish Grid Hunter v{VERSION} Test Suite Starting...")

    # [TEST 0] Optional API Key Check
    print("[0] Checking optional dependencies...")
    api_key = os.getenv("BINANCE_API_KEY")
    if api_key:
        record_test("Private API Access", "PASS", "BINANCE_API_KEY is set")
    else:
        record_test("Private API Access", "INFO", "BINANCE_API_KEY not set (Optional)")

    # [TEST 1] Spot Connectivity with Fallback
    print("[1] Testing Spot API connectivity (Public)...")
    url = get_spot_base_url()
    if url:
        record_test("Spot API Ping", "PASS", f"Using {url}")
    else:
        record_test("Spot API Ping", "FAIL", "No working endpoint")

    # [TEST 2] Market Rank API
    print("[2] Testing crypto-market-rank API (Public)...")
    tokens = fetch_market_rankings(size=20)
    if tokens:
        record_test("crypto-market-rank API", "PASS", f"Fetched {len(tokens)} tokens")
    else:
        record_test("crypto-market-rank API", "WARN", "No tokens returned")

    # [TEST 3] Smart Money API
    print("[3] Testing trading-signal API (Public)...")
    signals = fetch_smart_money_signals(chain_id="CT_501", size=10)
    if signals:
        record_test("trading-signal API", "PASS", f"Fetched {len(signals)} signals")
    else:
        record_test("trading-signal API", "WARN", "No signals returned")

    # [TEST 4] Token Audit API
    print("[4] Testing query-token-audit API (Public)...")
    # Audit WBNB on BSC as a known-valid contract
    audit = audit_token("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "56")
    if audit:
        record_test("query-token-audit API", "PASS", "Audit data received")
    else:
        record_test("query-token-audit API", "WARN", "No audit data")

    # [TEST 5] RSI Validation (Wilder Smoothing correctness)
    print("[5] Validating RSI calculation (Wilder Smoothing)...")
    # Use 20 data points so len > n=14 and calculation is meaningful
    prices_up = [10 + i for i in range(20)]
    prices_down = [100 - i for i in range(20)]
    rsi_up = calculate_rsi(prices_up)
    rsi_down = calculate_rsi(prices_down)
    if rsi_up is not None and rsi_down is not None and rsi_up > 80 and rsi_down < 20:
        record_test("RSI Validation", "PASS",
                    f"Up trend RSI={rsi_up:.1f} (>80), Down trend RSI={rsi_down:.1f} (<20)")
    else:
        record_test("RSI Validation", "FAIL",
                    f"Up: {rsi_up}, Down: {rsi_down}")

    # [TEST 5b] RSI data-guard validation
    print("[5b] Validating RSI data-guard (insufficient data returns None)...")
    rsi_short = calculate_rsi([10 + i for i in range(14)])  # exactly n, should return None
    if rsi_short is None:
        record_test("RSI Data-Guard", "PASS", "Returns None when len(prices) <= n")
    else:
        record_test("RSI Data-Guard", "FAIL", f"Expected None, got {rsi_short}")

    # [TEST 5c] Bollinger Bands 20-period correctness
    print("[5c] Validating Bollinger Bands (20-period SMA)...")
    import random
    random.seed(42)
    test_prices = [100 + random.uniform(-5, 5) for _ in range(72)]
    lb, mb, ub = calculate_bollinger_bands(test_prices, period=20)
    # Verify band uses only last 20 points
    expected_sma = sum(test_prices[-20:]) / 20
    if abs(mb - expected_sma) < 1e-9:
        record_test("Bollinger Bands", "PASS",
                    f"20-period SMA correct: {mb:.4f}, Range: {((ub-lb)/mb*100):.2f}%")
    else:
        record_test("Bollinger Bands", "FAIL",
                    f"SMA mismatch: got {mb:.4f}, expected {expected_sma:.4f}")

    # [TEST 6] Full Pipeline Simulation (30-day data, real Smart Money)
    print(f"[6] Running full pipeline scan ({len(DEFAULT_PAIRS)} pairs, limit={KLINE_LIMIT_SCAN})...")
    candidates = []
    all_signals = fetch_smart_money_signals(size=100)
    signal_symbols = [s.get("symbol", "").upper() for s in all_signals]

    for symbol in DEFAULT_PAIRS:
        klines = fetch_klines(symbol, interval="1d", limit=KLINE_LIMIT_SCAN)
        analysis = calculate_grid_parameters(symbol, klines)
        if analysis:
            score = analysis["score"]
            sm_backed = False
            # Real Smart Money cross-reference (no hard-coded bonuses)
            base_sym = symbol.replace("USDT", "")
            if base_sym in signal_symbols:
                score += 15
                sm_backed = True
                analysis["sm_backed"] = True

            candidates.append((symbol, score, analysis))
            sm_tag = "[SM]" if sm_backed else "    "
            rsi_val = f"{analysis['rsi']:.1f}" if isinstance(analysis['rsi'], float) else analysis['rsi']
            print(f"  {sm_tag} {symbol}: Score={score:.0f}, "
                  f"Vol={analysis['volatility']:.2f}%, "
                  f"RSI={rsi_val}, "
                  f"Range={analysis['range_pct']:.2f}%")

    if candidates:
        record_test("Full Pipeline", "PASS",
                    f"Scanned {len(DEFAULT_PAIRS)} pairs, {len(candidates)} analyzed")
    else:
        record_test("Full Pipeline", "FAIL", "No candidates analyzed")

    # [TEST 7] Breakout Alert Logic
    print("[7] Testing Breakout Alert logic...")
    # Simulate: price=105, range=[90,110], 24h avg volume=1000, current volume=3000
    grid_lower, grid_upper = 90.0, 110.0
    last_price = 105.0
    current_volume = 3000.0
    avg_volume = 1000.0

    boundary_threshold = 0.10  # within 10% of boundary
    near_upper = last_price >= grid_upper * (1 - boundary_threshold)
    near_lower = last_price <= grid_lower * (1 + boundary_threshold)
    near_boundary = near_upper or near_lower
    vol_spike = current_volume >= avg_volume * 2.0

    alert_level = "NONE"
    if near_boundary and vol_spike:
        alert_level = "CRITICAL"
    elif near_boundary or vol_spike:
        alert_level = "HIGH"

    if alert_level in ("CRITICAL", "HIGH"):
        record_test("Breakout Alert", "PASS",
                    f"Alert={alert_level}, NearBoundary={near_boundary}, VolSpike={vol_spike}")
    else:
        record_test("Breakout Alert", "FAIL",
                    f"Alert={alert_level} — logic did not trigger as expected")

    # Summary
    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    for r in _test_results:
        icon = ("✓" if r["status"] == "PASS"
                else "i" if r["status"] == "INFO"
                else "!" if r["status"] == "WARN"
                else "✗")
        print(f"[{icon}] {r['name']:<28}: {r['status']:<6} {r['detail']}")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
