# -*- coding: utf-8 -*-
import time, os
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from db.base import session_scope
import config as cfg

def now_utc():
    return datetime.utcnow().replace(tzinfo=timezone.utc)

def ts_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)

def human(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def main():
    os.makedirs("logs", exist_ok=True)

    t_end = now_utc()
    t_start = t_end - timedelta(days=1)
    t_start_ms = ts_ms(t_start)

    with session_scope() as s:
        # --- signals за 24ч ---
        total = s.execute(text("""
            SELECT COUNT(*) FROM signals WHERE ts_ms >= :ts_from
        """), {"ts_from": t_start_ms}).scalar() or 0

        cnt_buy = s.execute(text("""
            SELECT COUNT(*) FROM signals
            WHERE ts_ms >= :ts_from AND signal='BUY'
        """), {"ts_from": t_start_ms}).scalar() or 0

        cnt_sell = s.execute(text("""
            SELECT COUNT(*) FROM signals
            WHERE ts_ms >= :ts_from AND signal='SELL'
        """), {"ts_from": t_start_ms}).scalar() or 0

        cnt_cross_up_gap = s.execute(text("""
            SELECT COUNT(*) FROM signals
            WHERE ts_ms >= :ts_from AND reason='cross_up+gap'
        """), {"ts_from": t_start_ms}).scalar() or 0

        # последние 5 сигналов
        last_signals = s.execute(text("""
            SELECT ts_ms, pair, exchange, interval, signal, reason,
                   ROUND(ema_fast,6) AS ema_f, ROUND(ema_slow,6) AS ema_s,
                   ROUND(gap_bps,3)  AS gap_bps, exec_status
            FROM signals
            WHERE ts_ms >= :ts_from
            ORDER BY ts_ms DESC
            LIMIT 5
        """), {"ts_from": t_start_ms}).fetchall()

        # --- сделки DRY/LIVE ---
        # DRY: открытые сейчас
        dry_open = s.execute(text("""
            SELECT COUNT(*) FROM trades_dry WHERE is_open=1
        """)).scalar() or 0

        # DRY: открыто за 24ч
        dry_open_24h = s.execute(text("""
            SELECT COUNT(*) FROM trades_dry
            WHERE ts_open_ms IS NOT NULL AND ts_open_ms >= :ts_from
        """), {"ts_from": t_start_ms}).scalar() or 0

        # DRY: закрыто за 24ч
        dry_closed_24h = s.execute(text("""
            SELECT COUNT(*) FROM trades_dry
            WHERE ts_close_ms IS NOT NULL AND ts_close_ms >= :ts_from
        """), {"ts_from": t_start_ms}).scalar() or 0

        # LIVE: открытые сейчас
        live_open = s.execute(text("""
            SELECT COUNT(*) FROM trades_live WHERE is_open=1
        """)).scalar() or 0

        # Баланс
        base_quote = cfg.TRADE.get("BASE_QUOTE","USDC")
        w = s.execute(text("""
            SELECT free,locked,updated_ms FROM wallet WHERE asset=:a
        """), {"a": base_quote}).fetchone()
        free = float(w[0]) if w else 0.0
        locked = float(w[1]) if w else 0.0
        updated_ms = int(w[2]) if w and w[2] is not None else None

    # Формируем отчёт
    lines = []
    lines.append(f"# Daily report — {human(t_end)}")
    lines.append("")
    lines.append("## Signals (last 24h)")
    lines.append(f"- total: {total}")
    lines.append(f"- BUY: {cnt_buy}")
    lines.append(f"- SELL: {cnt_sell}")
    lines.append(f"- cross_up+gap: {cnt_cross_up_gap}")
    lines.append("")
    lines.append("Last signals:")
    if last_signals:
        for r in last_signals:
            ts_h = human(datetime.fromtimestamp(r[0]/1000, tz=timezone.utc))
            lines.append(f"  - {ts_h} | {r[1]}/{r[2]}/{r[3]} | {r[4]} ({r[5]}) | ema_f={r[6]} ema_s={r[7]} gap_bps={r[8]} exec={r[9]}")
    else:
        lines.append("  - no signals in last 24h")

    lines.append("")
    lines.append("## Trades")
    lines.append(f"- DRY open now: {dry_open}")
    lines.append(f"- DRY opened 24h: {dry_open_24h}")
    lines.append(f"- DRY closed 24h: {dry_closed_24h}")
    lines.append(f"- LIVE open now: {live_open}")

    lines.append("")
    lines.append("## Wallet")
    upd_h = human(datetime.fromtimestamp(updated_ms/1000, tz=timezone.utc)) if updated_ms else "n/a"
    lines.append(f"- {base_quote} free={free:.2f} locked={locked:.2f} (updated: {upd_h})")

    report = "\n".join(lines) + "\n"

    # Пишем в общий лог и в файл дня
    try:
        with open("logs/daily_report.log","a",encoding="utf-8") as f:
            f.write(report)
    except Exception:
        pass

    try:
        day_name = now_utc().strftime("logs/daily_report-%Y%m%d.txt")
        with open(day_name,"w",encoding="utf-8") as f:
            f.write(report)
    except Exception:
        pass

    # Опционально: попытаться отправить нотификацию (короткую)
    try:
        import notify
        notify.simple_notify(f"[Daily] total={total}, BUY={cnt_buy}, SELL={cnt_sell}, dry_open={dry_open}")
    except Exception:
        pass

if __name__ == "__main__":
    main()
