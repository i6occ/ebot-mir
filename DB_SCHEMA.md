# DB_SCHEMA — описание структуры таблиц (без данных)

> Назначение файла: дать ИИ (и людям) представление о структуре БД.
> Реальные секреты/доступы отсутствуют. Данные не выгружаются.

## Общие соглашения
- Временные метки: Unix ms (`BIGINT`), если не оговорено иначе.
- Денежные и ценовые поля: DECIMAL(20,8) или аналогичный high‑precision тип.
- JSON‑поля хранят произвольную мета‑информацию по сделке/заявкам/ошибкам.

---

## Таблицы сделок

### trades_dry
Симулированные сделки (dry‑run).
- `id`               INTEGER PRIMARY KEY AUTOINCREMENT
- `symbol`           TEXT            — торговая пара (напр., "BTCUSDC")
- `exchange`         TEXT            — биржа (напр., "MEXC")
- `interval`         TEXT            — таймфрейм (напр., "1m")
- `side`             TEXT            — 'BUY' | 'SELL'
- `qty`              DECIMAL(20,8)   — количество базового актива
- `entry_price`      DECIMAL(20,8)
- `exit_price`       DECIMAL(20,8)   — nullable, пока позиция не закрыта
- `opened_at`        BIGINT          — ts открытия, ms
- `closed_at`        BIGINT          — ts закрытия, ms, nullable
- `fee_quote`        DECIMAL(20,8)   — комиссия в котируемой валюте
- `pnl_quote`        DECIMAL(20,8)   — PnL в котируемой валюте
- `order_ids`        TEXT            — JSON массив id ордеров
- `meta`             TEXT            — JSON произвольных полей

### trades_live
Реальные сделки (live‑режим). Поля идентичны `trades_dry`.

---

## Таблицы котировок/свечей (если включены сборщики)

### candles_1m
Минутные свечи по активным символам/биржам (если запущены `candles_fetch`/`candles_increment`).
- `id`        INTEGER PRIMARY KEY AUTOINCREMENT
- `symbol`    TEXT
- `exchange`  TEXT
- `ts`        BIGINT         — метка открытия свечи, ms
- `open`      DECIMAL(20,8)
- `high`      DECIMAL(20,8)
- `low`       DECIMAL(20,8)
- `close`     DECIMAL(20,8)
- `volume`    DECIMAL(28,8)

> Примечание: имя таблицы/индексов может отличаться в вашей реализации;
> цель — зафиксировать структуру, которой ожидают сервисы.

---

## Балансы/кошелёк (если включён сборник балансов)

### wallets_snapshot
Срез балансов по бирже/активу.
- `id`        INTEGER PRIMARY KEY AUTOINCREMENT
- `exchange`  TEXT
- `asset`     TEXT            — тикер (USDC, BTC и т.п.)
- `free`      DECIMAL(28,8)
- `locked`    DECIMAL(28,8)
- `ts`        BIGINT          — время среза, ms
- `meta`      TEXT            — JSON (например, статус/ошибки API)

---

## Индексы/уникальности (рекомендации)
- `candles_1m`: UNIQUE(`exchange`,`symbol`,`ts`)
- `trades_*`: индексы на (`exchange`,`symbol`,`opened_at`) и (`closed_at`)
- `wallets_snapshot`: индексы на (`exchange`,`asset`,`ts`)

---

## Служебные заметки
- Фактические названия таблиц/полей возьмите из текущих миграций/моделей.
- Этот файл предназначен для анализа ИИ и документации. Данных нет.
