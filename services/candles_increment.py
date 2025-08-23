# -*- coding: utf-8 -*-
import time
from datetime import datetime, timezone
from math import floor

from db.base import session_scope
from db.models import Candle, CurrentPrice
import config as cfg

PAIR = cfg.STRATEGY["PAIRS"][0]
SYMBOL = PAIR["symbol"]
EXCHANGE = PAIR["exchange"]
INTERVAL = PAIR["interval"]  # "1m"
REFRESH_SEC = int(cfg.CANDLES.get("LIVE_REFRESH_SEC", 3))

def _floor_minute_ts_ms(ts_ms: int) -> int:
    return (ts_ms // 60000) * 60000

def _now_ms() -> int:
    return int(time.time() * 1000)

def _last_price_usdc():
    with session_scope() as s:
        r = s.query(CurrentPrice).order_by(CurrentPrice.ts_ms.desc()).limit(1).first()
        if not r: return None
        # берём median/mexc_mid -> в USDC
        px = r.current_median or r.mexc_mid
        return float(px) if px else None

def _upsert_bar(ts_ms: int, price: float):
    with session_scope() as s:
        pk = dict(pair=SYMBOL, exchange=EXCHANGE, interval=INTERVAL, ts_ms=ts_ms)
        row = s.get(Candle, (SYMBOL, EXCHANGE, INTERVAL, ts_ms))
        if row is None:
            row = Candle(**pk, open=price, high=price, low=price, close=price, volume=0.0)
            s.add(row)
        else:
            # обновляем close и расширяем high/low
            row.close = price
            if row.high is None or price > row.high: row.high = price
            if row.low  is None or price < row.low:  row.low  = price

def run_once():
    price = _last_price_usdc()
    if price is None:
        return {"status":"skip","reason":"no_price"}

    now = _now_ms()
    i_ts = _floor_minute_ts_ms(now)
    ts_list = [i_ts - 2*60000, i_ts - 1*60000, i_ts]  # i-2, i-1, i

    for ts in ts_list:
        _upsert_bar(ts, price)

    return {"status":"ok","bars":len(ts_list),"price":price}

if __name__ == "__main__":
    try:
        res = run_once()
        print("candles_increment:", res)
    except Exception as e:
        print("candles_increment_error:", repr(e))
