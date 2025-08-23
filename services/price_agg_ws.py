# -*- coding: utf-8 -*-
import time, json, traceback, requests
from typing import Optional
import config as cfg
from db.base import session_scope
from db.models import CurrentPrice

MEXC_TICKER_URL = "https://api.mexc.com/api/v3/ticker/bookTicker"
SYMBOL = "BTCUSDC"
USDCUSDT_SYMBOL = "USDCUSDT"
POLL_SEC = int(getattr(cfg, "CURRENT_PRICE", {}).get("USDCUSDT_POLL_SEC", 5))  # from config.py


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mid_from_book(resp_json) -> Optional[float]:
    try:
        bid = float(resp_json["bidPrice"])
        ask = float(resp_json["askPrice"])
        if bid > 0 and ask > 0:
            return (bid + ask) / 2.0
    except Exception:
        pass
    return None


def fetch_pair(symbol: str) -> Optional[float]:
    try:
        r = requests.get(MEXC_TICKER_URL, params={"symbol": symbol}, timeout=5)
        if r.status_code != 200:
            return None
        j = r.json()
        return _mid_from_book(j)
    except Exception:
        return None


def main_loop():
    while True:
        ts = int(time.time() * 1000)
        mexc_mid = fetch_pair(SYMBOL)
        usdcusdt = fetch_pair(USDCUSDT_SYMBOL)

        current_median = mexc_mid if mexc_mid is not None else None

        with session_scope() as s:
            row = CurrentPrice(
                ts_ms=ts,
                current_median=current_median,
                mexc_mid=mexc_mid,
                binance_mid=None,
                bybit_mid=None,
                usdc_usdt_rate=usdcusdt,
                mode="REST",
                sources_count=int(mexc_mid is not None)
            )
            s.add(row)

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main_loop()
