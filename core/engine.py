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

    # Если есть открытая позиция — приоритизируем её ведение/закрытие
    if has_open(symbol, exchange, interval):
        t = get_open(symbol, exchange, interval)

        # 1) Закрытие по сигналу SELL
        if signal == "SELL" and t and t.base_qty and price:
            try:
                proceeds = float(t.base_qty) * float(price)
                add_free(base_quote, proceeds)  # пополняем кошелёк выручкой
                close_entry(symbol, exchange, interval, price, meta={"src": "engine_sell"})
                # оценка pnl%
                try:
                    entry = float(t.entry_price) if t and t.entry_price else None
                    pnl_pct = (float(price) - entry) / entry if (entry and entry > 0) else None
                except Exception:
                    pnl_pct = None
                # нотификация
                try:
                    qty = float(t.base_qty) if t and t.base_qty else 0.0
                    notify.trade_notify("SELL", symbol, exchange, qty, float(price), pnl_pct)
                except Exception:
                    pass
                return {"status": "closed"}
            except Exception:
                # не блокируем цикл, если закрытие не удалось
                return {"status": "error", "reason": "sell_close_failed"}

        # 2) Стоп-лосс: цена упала ниже входа на SL-процент — закрываем
        if t and t.entry_price and price and float(price) <= float(t.entry_price) * (1.0 - sl_pct):
            proceeds = float(t.base_qty or 0.0) * float(price)
            add_free(base_quote, proceeds)
            close_entry(symbol, exchange, interval, price, meta={"src": "engine_sl"})
            # Нотификация по SL (pnl% оценим относительно entry)
            try:
                entry = float(t.entry_price) if t and t.entry_price else None
                pnl_pct = (float(price) - entry) / entry if (entry and entry > 0) else None
            except Exception:
                pnl_pct = None
            try:
                qty = float(t.base_qty) if t and t.base_qty else 0.0
                notify.trade_notify("SELL", symbol, exchange, qty, float(price), pnl_pct)
            except Exception:
                pass
            return {"status": "closed"}

        # Если позиция есть, но ни SELL, ни SL — держим
        return {"status": "hold"}

    # Нет открытой позиции — рассматриваем BUY
    if signal == "BUY" and not has_open(symbol, exchange, interval):
        quote_free = get_free(base_quote)
        alloc_pct = float(cfg.TRADE.get("ALLOC_PCT", 5.0)) / 100.0
        spend = max(0.0, quote_free * alloc_pct)
        if spend <= 0:
            return {"status": "skip", "reason": "no_quote"}
        if not price or float(price) <= 0:
            return {"status": "skip", "reason": "bad_price"}

        base_qty = spend / float(price)

        # списываем из кошелька и открываем сделку с фиксацией потраченной котировки
        add_free(base_quote, -spend)
        open_entry(symbol, exchange, interval, price, base_qty, spend, meta={"src": "engine_buy"})

        try:
            notify.trade_notify("BUY", symbol, exchange, float(base_qty), float(price), None)
        except Exception:
            pass
        return {"status": "open"}

    # По умолчанию — удерживаем
    return {"status": "hold"}
