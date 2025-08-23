# CHECKLIST_Ebot_DRY_issues.md

## Цель
Разобрать причины отсутствия сделок в DRY, починить логирование сигналов, обеспечить корректный выбор таблиц DRY/LIVE, валидировать таймстемпы и поставить мониторинг+отчёты.

---

## 1. Время и таймзона
- [x] timedatectl → UTC, NTP active.
- [x] Все метки в БД — Unix ms (UTC).
- [x] Будущих ts нет (допуск +2 мин).

Быстрая проверка:

timedatectl status | sed -n '1,10p'

python3 - <<PY
import sqlite3, time
now_ms = int(time.time()*1000) + 120000
con = sqlite3.connect("data/ebot.db")
cur = con.cursor()
for name, sql in [
  ("candles_future", "SELECT COUNT(*) FROM candles WHERE ts_ms > ?"),
  ("current_price_future", "SELECT COUNT(*) FROM current_price WHERE ts_ms > ?"),
]:
    cnt = cur.execute(sql, (now_ms,)).fetchone()[0]
    print(name, cnt)
con.close()
PY

