# -*- coding: utf-8 -*-
from db.trades_io import has_open, open_entry, close_entry, get_open
from db.wallet import get_free, add_free
import config as cfg
import notify
from math import isfinite

def process_signal(symbol, exchange, interval, signal, price):
    base_quote = cfg.TRADE.get("BASE_QUOTE", "USDC")
    # SL: если есть открытая и цена упала ниже входа на STOP_LOSS_PCT -> закрыть
    sl_pct = float(getattr(cfg, "RISK", {}).get("STOP_LOSS_PCT", 0.005))
    if has_open(symbol, exchange, interval):
        t = get_open(symbol, exchange, interval)
        if t and t.entry_price and price and float(price) <= float(t.entry_price) * (1.0 - sl_pct):
            proceeds = float(t.base_qty or 0.0) * float(price)
            add_free(base_quote, proceeds)
            close_entry(symbol, exchange, interval, price, meta={"src":"engine"})
        try:
            t = get_open(symbol, exchange, interval)  # уже закрыта, но у нас t был до close выше; на случай отсутствия возьмём last
        except Exception:
            t = None
        try:
            # оценим pnl % по entry vs текущей цене выхода
            entry = float(t.entry_price) if t and t.entry_price else None
            pnl_pct = (float(price) - entry)/entry if (entry and entry>0) else None
        except Exception:
            pnl_pct = None
        try:
            qty = float(t.base_qty) if t and t.base_qty else 0.0
            notify.trade_notify("SELL", symbol, exchange, qty, float(price), pnl_pct)
        except Exception:
            pass
        return {"status":"closed"}
    if signal == "BUY" and not has_open(symbol, exchange, interval):
        quote_free = get_free(base_quote)
        alloc_pct = float(cfg.TRADE.get("ALLOC_PCT", 5.0)) / 100.0
        spend = max(0.0, quote_free * alloc_pct)
        if spend <= 0:
            return {"status": "skip", "reason": "no_quote"}
        base_qty = 0.0 if price == 0 else spend / float(price)
        open_entry(symbol, exchange, interval, price, base_qty, meta={"src":"engine"})
        try:
            notify.trade_notify("BUY", symbol, exchange, float(base_qty), float(price), None)
        except Exception:
            pass
        return {"status":"open"}
        # PnL учтём позже
        return {"status": "closed"}
    return {"status": "hold"}
