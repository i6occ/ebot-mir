# -*- coding: utf-8 -*-
"""
Telegram notifications for trades (BUY/SELL) + equity snapshot for 24h PnL.

Сообщение:
DRY/LIVE / BTCUSDC
BUY/SELL: <qty>
PRICE: <price>
BAL: <free USDC> [±pnl% только для SELL]
-----------------
<MSK datetime>
TOTAL: <equity $> / <24h %>
"""
from __future__ import annotations

import json
import time
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta

import requests

# --- helpers ---

def _cfg():
    import importlib.util as u
    s = u.spec_from_file_location('config', '/root/Ebot/config.py')
    m = u.module_from_spec(s); s.loader.exec_module(m)
    return m

def _msk_now_str(ts_ms: Optional[int] = None) -> str:
    if ts_ms is None:
        dt = datetime.now(timezone.utc)
    else:
        dt = datetime.fromtimestamp(int(ts_ms) / 1000.0, tz=timezone.utc)
    # MSK = UTC+3
    dt = dt.astimezone(timezone(timedelta(hours=3)))
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _latest_price_and_rate() -> Tuple[float, float]:
    """
    Возвращает (last_price_usdc, usdc_usdt_rate).
    """
    try:
        from db.base import session_scope
        from db.models import CurrentPrice
        with session_scope() as s:
            r = s.query(CurrentPrice).order_by(CurrentPrice.ts_ms.desc()).limit(1).first()
            if r:
                price_now = float((r.current_median or r.mexc_mid) or 0.0)
                rate = float(r.usdc_usdt_rate or 1.0)
                return price_now, rate
    except Exception:
        pass
    return 0.0, 1.0

def _current_equity_usdc() -> float:
    """
    Equity в USDC: free USDC + сумма открытых позиций (qty * last_price_usdc).
    """
    try:
        cfg = _cfg()
        base_quote = cfg.TRADE.get("BASE_QUOTE", "USDC")
        from db.base import session_scope
        from db.models import Wallet, TradeDry, TradeLive
        price_now, _ = _latest_price_and_rate()
        with session_scope() as s:
            w = s.get(Wallet, base_quote)
            free = float(w.free) if w else 0.0
            T = TradeDry if getattr(cfg, "DRY_RUN", True) else TradeLive
            open_usdc = 0.0
            for t in s.query(T).filter(T.is_open == True).all():  # noqa: E712
                open_usdc += float(t.base_qty or 0.0) * float(price_now or 0.0)
            return free + open_usdc
    except Exception:
        return 0.0

def _equity_24h_change_pct(cur_usdc: float) -> float:
    """
    Сохраняет снапшоты equity и возвращает изменение за 24ч в долях (0.05 = +5%).
    """
    import os
    data_dir = "/root/Ebot/data"
    os.makedirs(data_dir, exist_ok=True)
    path = f"{data_dir}/equity_24h.jsonl"
    now_ms = int(time.time() * 1000)

    snaps = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    snaps.append(json.loads(line))
                except Exception:
                    pass

    # добавляем текущий
    snaps.append({"ts_ms": now_ms, "equity": float(cur_usdc)})
    # чистим старше 48ч
    snaps = [x for x in snaps if (now_ms - int(x.get("ts_ms", 0))) <= 48 * 3600 * 1000]

    # сохраняем
    with open(path, "w", encoding="utf-8") as f:
        for x in snaps:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    # ищем ближайший к -24ч
    target = now_ms - 24 * 3600 * 1000
    closest, best = None, None
    for x in snaps:
        dt = abs(int(x["ts_ms"]) - target)
        if best is None or dt < best:
            best = dt; closest = x
    if closest and closest.get("equity", 0) > 0:
        base = float(closest["equity"])
        if base > 0:
            return (float(cur_usdc) - base) / base
    return 0.0

# --- Telegram ---

def _tg_params():
    cfg = _cfg()
    tgd = getattr(cfg, "TELEGRAM", {})
    enabled = bool(tgd.get("ENABLED", True)) and bool(tgd.get("BOT_TOKEN")) and bool(tgd.get("CHAT_ID"))
    return enabled, tgd.get("BOT_TOKEN", ""), tgd.get("CHAT_ID", "")

def send_text(text: str) -> bool:
    """
    Отправка plain‑текста в Telegram. Возвращает True/False по ответу API.
    """
    enabled, token, chat_id = _tg_params()
    if not enabled:
        print("[TG] disabled")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=5,
        )
        try:
            js = resp.json()
            ok = bool(js.get("ok"))
            desc = js.get("description")
            print(f"[TG] HTTP {resp.status_code} ok={ok} desc={desc}")
            return ok
        except Exception as e:
            print(f"[TG] HTTP {getattr(resp,'status_code',None)} json_err={e}")
            return False
    except Exception as e:
        print(f"[TG] send err: {e}")
        return False

# --- Public API ---

def trade_notify(
    action: str,
    symbol: str,
    exchange: str,
    qty: float,
    price: float,
    pnl_pct: Optional[float],
    ts_ms: Optional[int] = None
) -> bool:
    """
    Формирует и отправляет сообщение о сделке (BUY/SELL) в Telegram.
    """
    cfg = _cfg()
    mode = "DRY" if getattr(cfg, "DRY_RUN", True) else "LIVE"

    # расчёты
    price_now_usdc, usdc_usdt = _latest_price_and_rate()
    equity_usdc = _current_equity_usdc()
    equity_usd = equity_usdc * (usdc_usdt or 1.0)
    eq24 = _equity_24h_change_pct(equity_usdc)

    # баланс после операции
    try:
        from db.base import session_scope
        from db.models import Wallet
        base_quote = cfg.TRADE.get("BASE_QUOTE", "USDC")
        with session_scope() as s:
            w = s.get(Wallet, base_quote)
            bal_free = float(w.free) if w else 0.0
    except Exception:
        bal_free = 0.0

    # формат
    sign = "+" if (pnl_pct or 0) >= 0 else ""
    pnl_str = f" {sign}{(pnl_pct or 0) * 100:.2f}%" if (pnl_pct is not None) else ""
    dt_str = _msk_now_str(ts_ms)
    total_line = f"TOTAL: {equity_usd:,.2f} $ / {eq24*100:+.0f}%".replace(",", " ")

    text = (
        f"{mode} / {symbol}\n"
        f"{action.upper()}: {qty:.8f}\n"
        f"PRICE: {price:.2f}\n"
        f"BAL: {bal_free:.2f} USDC{pnl_str}\n"
        f"-----------------\n"
        f"{dt_str}\n"
        f"{total_line}"
    )
    return send_text(text)

# --- manual test ---
if __name__ == "__main__":
    # небольшой самотест, если запустить файл руками
    ok = send_text("✅ notify.py ready")
    print("selftest:", ok)
