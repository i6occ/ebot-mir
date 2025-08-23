# -*- coding: utf-8 -*-
import time, math
from typing import List, Dict
import requests
from db.base import session_scope
from db.models import Candle

API = "https://api.mexc.com/api/v3/klines"
SYMBOL = "BTCUSDC"
INTERVAL = "1m"
CHUNK = 1000  # макс. у MEXC

def save_klines(rows: List[List]):
    with session_scope() as s:
        for r in rows:
            ts = int(r[0])            # open time ms
            open_, high, low, close = map(float, (r[1], r[2], r[3], r[4]))
            vol = float(r[5])
            c = Candle(pair=SYMBOL, exchange="MEXC", interval=INTERVAL, ts_ms=ts,
                       open=open_, high=high, low=low, close=close, volume=vol)
            s.merge(c)  # upsert

def fetch_chunk(end_ms: int):
    params = {"symbol": SYMBOL, "interval": INTERVAL, "limit": CHUNK, "endTime": end_ms}
    r = requests.get(API, params=params, timeout=10)
    r.raise_for_status()
    rows = r.json()
    return rows

def backfill(minutes: int = 2000):
    now = int(time.time()*1000)
    need = minutes
    end_ms = now
    while need > 0:
        rows = fetch_chunk(end_ms)
        if not rows:
            break
        save_klines(rows)
        first_ts = int(rows[0][0])
        got = len(rows)
        need -= got
        end_ms = first_ts - 1
        time.sleep(0.2)

if __name__ == "__main__":
    backfill(2000)
