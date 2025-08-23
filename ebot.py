# -*- coding: utf-8 -*-
import config as cfg
from db.base import create_all, session_scope
from db.models import Candle, CurrentPrice
from db.wallet import ensure_start_balance, get_free
from core.engine import process_signal
from core.core import compute_signal

def _load_closes(symbol, exchange, interval, limit=500):
    with session_scope() as s:
        rows = (s.query(Candle.close)
                  .filter(Candle.pair==symbol, Candle.exchange==exchange, Candle.interval==interval)
                  .order_by(Candle.ts_ms.asc())
                  .all())
        closes = [float(r[0]) for r in rows][-limit:]
        return closes

def _last_price_fallback(symbol_close_list):
    # текущая медиана из current_price; если нет — последний close
    with session_scope() as s:
        last = s.query(CurrentPrice).order_by(CurrentPrice.ts_ms.desc()).limit(1).first()
        if last and last.current_median:
            return float(last.current_median)
    return float(symbol_close_list[-1]) if symbol_close_list else 0.0

def main():
    create_all()
    ensure_start_balance()
    pair = cfg.STRATEGY["PAIRS"][0]
    symbol, exchange, interval = pair["symbol"], pair["exchange"], pair["interval"]

    closes = _load_closes(symbol, exchange, interval, limit=max(300, cfg.STRATEGY.get("EMA_SLOW",20)*3))
    price  = _last_price_fallback(closes)
    signal, meta = compute_signal(
        closes, price,
        ema_fast=cfg.STRATEGY.get("EMA_FAST",9),
        ema_slow=cfg.STRATEGY.get("EMA_SLOW",20),
        entry_min_gap_pct=cfg.STRATEGY.get("ENTRY_MIN_GAP_PCT",0.0005),
        cross_grace_bars=cfg.STRATEGY.get("CROSS_GRACE_BARS",3)
    )
    res = process_signal(symbol, exchange, interval, signal, price)
    print("tick:", {"signal": signal, "meta": meta, "exec": res, "price": price,
                    "quote_free": get_free(cfg.TRADE.get("BASE_QUOTE","USDC"))})

if __name__ == "__main__":
    main()
