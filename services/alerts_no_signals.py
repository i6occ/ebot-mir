# -*- coding: utf-8 -*-
import time
from datetime import datetime, timezone
from db.base import session_scope
from sqlalchemy import text

def now_ms():
    return int(time.time()*1000)

def main():
    ts_from = int((time.time() - 24*3600) * 1000)
    with session_scope() as s:
        # BUY кандидаты = BUY сигнал или reason=cross_up+gap
        row = s.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM signals
                WHERE ts_ms >= :ts_from
                  AND (signal='BUY' OR reason='cross_up+gap')
            """),
            {"ts_from": ts_from}
        ).fetchone()
        cnt = int(row[0] if row and row[0] is not None else 0)

    human = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    if cnt == 0:
        msg = f"[ALERT] {human} — нет BUY-кандидатов за последние 24ч"
        try:
            import notify
            # лёгкая нотификация, если настроен телеграм
            notify.simple_notify(msg)
        except Exception:
            pass
        try:
            with open("logs/alerts.log", "a", encoding="utf-8") as f:
                f.write(f"{now_ms()} | {msg}\n")
        except Exception:
            pass
    else:
        try:
            with open("logs/alerts.log", "a", encoding="utf-8") as f:
                f.write(f"{now_ms()} | OK: {cnt} BUY-кандидатов за 24ч\n")
        except Exception:
            pass

if __name__ == "__main__":
    main()
