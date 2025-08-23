#!/usr/bin/env python3
# report_status.py — строит график из БД и шлёт в Telegram (напрямую) + caption с 5 последними сделками

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests

ROOT = Path("/root/Ebot")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.charts_core import make_candles_png
from db.base import session_scope
from db.models import TradeDry, TradeLive
from config import STRATEGY, TELEGRAM
try:
    from config import CHARTS
except Exception:
    CHARTS = {}

MSK = timezone(timedelta(hours=3), name="MSK")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=None)
    p.add_argument("--legend", type=str, default=None)
    p.add_argument("--pair", type=str, default=None)  # формат: BTCUSDC@MEXC
    p.add_argument("--tf", type=str, default=None)    # напр.: 1m
    return p.parse_args()

def send_photo(token: str, chat_id: str, photo_path: str, caption: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(photo_path, "rb") as fh:
        r = requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"photo": fh}, timeout=8)
    ok = r.ok and r.json().get("ok")
    if not ok:
        print(f"[TG] sendPhoto failed: {r.status_code} {r.text[:200]}")
    return bool(ok)

def send_text(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=6)
    return bool(r.ok and r.json().get("ok"))

def pick_pair(args):
    if args.pair and "@" in args.pair:
        sym, ex = args.pair.split("@", 1)
        tf = args.tf or "1m"
        return dict(symbol=sym, exchange=ex, interval=tf)
    pairs = STRATEGY.get("PAIRS", [])
    mx = [p for p in pairs if p.get("exchange") == "MEXC"]
    if not pairs:
        raise RuntimeError("STRATEGY.PAIRS is empty")
    p = (mx or pairs)[0]
    if args.tf:
        p = dict(p); p["interval"] = args.tf
    return p

def last_trades_caption(symbol: str, exchange: str, limit: int = 5) -> str:
    mode_dry = True
    try:
        from config import DRY_RUN
        mode_dry = bool(DRY_RUN)
    except Exception:
        pass
    Model = TradeDry if mode_dry else TradeLive

    rows = []
    try:
        with session_scope() as s:
            rows = (s.query(Model)
                      .filter(Model.symbol==symbol, Model.exchange==exchange)
                      .order_by(Model.id.desc())
                      .limit(limit)
                      .all())
    except Exception as e:
        print("[WARN] trades fetch:", e)

    header = f"{symbol} @ {exchange} ({'DRY' if mode_dry else 'LIVE'})"
    if not rows:
        return header + "\nСделок ещё нет"

    lines = []
    for r in reversed(rows):
        dt_open  = datetime.fromtimestamp((r.ts_open_ms or 0)/1000, tz=MSK).strftime("%m-%d %H:%M")
        dt_close = datetime.fromtimestamp((r.ts_close_ms or 0)/1000, tz=MSK).strftime("%m-%d %H:%M") if r.ts_close_ms else "OPEN"
        qty = (r.base_qty or 0.0)
        ep  = r.entry_price or 0.0
        xp  = r.exit_price if (r.exit_price is not None) else "-"
        state = "OPEN" if r.is_open else "CLOSE"
        lines.append(f"{dt_open} → {dt_close} | {qty:.8f} | {ep:.2f} → {xp} | {state}")
    return header + "\n" + "\n".join(lines)

def main():
    args = parse_args()
    n = int(args.n or CHARTS.get("REPORT_CANDLES", 80) or 80)
    legend_loc = args.legend or CHARTS.get("LEGEND_LOC", "upper left")

    tok = TELEGRAM.get("BOT_TOKEN"); cid = TELEGRAM.get("CHAT_ID")
    tg_on = bool(TELEGRAM.get("ENABLED")) and bool(tok) and bool(cid)

    pair = pick_pair(args)
    sym, ex, tf = pair["symbol"], pair["exchange"], pair.get("interval", "1m")

    out_dir = ROOT / "tmp"; out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / f"chart_{sym}_{ex}_{tf}.png"

    png_path, _ = make_candles_png(
        sym, ex, tf, str(out_png),
        n=n,
        ema_fast=int(STRATEGY.get("EMA_FAST", 9)),
        ema_slow=int(STRATEGY.get("EMA_SLOW", 20)),
        mid_smooth=int(CHARTS.get("MID_SMOOTH", 9)),
        legend_loc=legend_loc
    )

    if not png_path:
        msg = f"⚠️ Нет данных для {sym}@{ex} ({tf})"
        print(msg)
        if tg_on: send_text(tok, cid, msg)
        return 0

    caption = last_trades_caption(sym, ex, limit=5)
    if tg_on:
        ok = send_photo(tok, cid, png_path, caption=caption)
        print(f"[TG] photo={ok}  path={png_path}")
    else:
        print(f"[INFO] TG disabled; saved: {png_path}\n---\n{caption}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
