# -*- coding: utf-8 -*-
import time, json
import config as cfg
from db.base import create_all, session_scope
from db.models import Candle, CurrentPrice, Signal
from db.wallet import ensure_start_balance, get_free
from core.engine import process_signal
from core.core import compute_signal

def _load_closes(symbol, exchange, interval, limit=500):
    with session_scope() as s:
        rows = (
            s.query(Candle.close)
            .filter(Candle.pair == symbol, Candle.exchange == exchange, Candle.interval == interval)
            .order_by(Candle.ts_ms.asc())
            .all()
        )
        return [float(r[0]) for r in rows][-limit:]

def _last_price_fallback(symbol_close_list):
    # текущая медиана из current_price; если нет — последний close
    with session_scope() as s:
        last = (
            s.query(CurrentPrice)
            .order_by(CurrentPrice.ts_ms.desc())
            .limit(1)
            .first()
        )
        if last and last.current_median:
            return float(last.current_median)
    return float(symbol_close_list[-1]) if symbol_close_list else 0.0

def main():
    create_all()
    ensure_start_balance()

    pair = cfg.STRATEGY["PAIRS"][0]
    symbol, exchange, interval = pair["symbol"], pair["exchange"], pair["interval"]

    closes = _load_closes(
        symbol,
        exchange,
        interval,
        limit=max(300, cfg.STRATEGY.get("EMA_SLOW", 20) * 3),
    )
    price = _last_price_fallback(closes)

    # ЕДИНЫЙ порог: GAP_THRESHOLD_BPS (bps) -> доля
    gap_pct = float(cfg.STRATEGY.get("GAP_THRESHOLD_BPS", 50)) / 10000.0

    signal, meta = compute_signal(
        closes,
        price,
        ema_fast=cfg.STRATEGY.get("EMA_FAST", 9),
        ema_slow=cfg.STRATEGY.get("EMA_SLOW", 20),
        entry_min_gap_pct=gap_pct,
        cross_grace_bars=cfg.STRATEGY.get("CROSS_GRACE_BARS", 3),
    )

    res = process_signal(symbol, exchange, interval, signal, price)
    quote_free = get_free(cfg.TRADE.get("BASE_QUOTE", "USDC"))

    payload = {
        "signal": signal,
        "meta": meta,
        "exec": res,
        "price": price,
        "quote_free": quote_free,
    }
    print("tick:", payload)

    # --- Лог в файл ---
    try:
        ts_ms = int(time.time() * 1000)
        human_ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts_ms / 1000))
        with open("logs/signals.log", "a", encoding="utf-8") as f:
            f.write(f"{ts_ms} | {human_ts} | tick: {payload}\n")
    except Exception:
        pass

    # --- Лог в БД (ORM) ---
    try:
        ema_fast = float(meta.get("ema9")) if isinstance(meta, dict) and meta.get("ema9") is not None else None
        ema_slow = float(meta.get("ema20")) if isinstance(meta, dict) and meta.get("ema20") is not None else None
        gap_bps = None
        if isinstance(meta, dict) and meta.get("gap") is not None:
            gap_bps = float(meta["gap"]) * 10000.0
        else:
            try:
                if ema_fast is not None and ema_slow is not None and price:
                    gap_bps = ((ema_fast - ema_slow) / float(price)) * 10000.0
            except Exception:
                gap_bps = None

        with session_scope() as s:
            s.add(Signal(
                ts_ms=int(time.time()*1000),
                pair=symbol,
                exchange=exchange,
                interval=interval,
                signal=signal,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                gap_bps=gap_bps,
                exec_status=(res.get("status") if isinstance(res, dict) else None),
                reason=(meta.get("reason") if isinstance(meta, dict) else None),
                meta_json=(json.dumps(meta, ensure_ascii=False) if isinstance(meta, dict) else None),
            ))
    except Exception:
        # не валим цикл из-за логирования
        pass

if __name__ == "__main__":
    main()

# !!! ВАЖНО: этот файл всегда выдавать одним блоком для копирования
# без форматирования и символов, которые могут порвать блок.
