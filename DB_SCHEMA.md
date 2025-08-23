# DB_SCHEMA.md (актуальная схема БД, SQLite)

> Файл БД по умолчанию: **data/ebot.db** (если `DB_URL=None`).  
> Все метки времени — **UTC в миллисекундах** (`ts_ms`).  
> Названия столбцов и таблиц синхронизированы с `db/models.py` и VARIABLES.md.

---

## Таблица: `candles`
OHLCV‑свечи по парам/биржам/интервалам.

**PK (составной):** `(pair, exchange, interval, ts_ms)`

| колонка     | тип        | описание                               |
|-------------|------------|-----------------------------------------|
| pair        | TEXT       | символ пары, напр. `BTCUSDT`            |
| exchange    | TEXT       | биржа, напр. `MEXC`                     |
| interval    | TEXT       | интервал, напр. `1m`, `5m`, `1h`        |
| ts_ms       | INTEGER    | время открытия свечи, UTC ms            |
| open        | REAL       |                                         |
| high        | REAL       |                                         |
| low         | REAL       |                                         |
| close       | REAL       |                                         |
| volume      | REAL       |                                         |

Индексы (рекоменд.):  
- `INDEX candles_idx_time ON candles(pair, exchange, interval, ts_ms DESC)`

---

## Таблица: `current_price`
Агрегированный «текущий» прайс и источники.

| колонка         | тип     | описание                            |
|-----------------|---------|------------------------------------|
| ts_ms           | INTEGER | UTC ms                             |
| current_median  | REAL    | медианный текущий прайс            |
| mexc_mid        | REAL    | mid по MEXC                        |
| binance_mid     | REAL    | mid по Binance                     |
| bybit_mid       | REAL    | mid по Bybit                       |
| usdc_usdt_rate  | REAL    | курс USDC/USDT                     |
| mode            | TEXT    | режим агрегации                    |
| sources_count   | INTEGER | число источников                   |

Индексы:  
- `INDEX current_price_idx_time ON current_price(ts_ms DESC)`

---

## Таблица: `trades_dry`
Сделки в DRY‑режиме (симуляция).

| колонка       | тип     | описание                               |
|---------------|---------|-----------------------------------------|
| id            | INTEGER | PK AUTOINCREMENT                        |
| ts_open_ms    | INTEGER | UTC ms открытия                         |
| ts_close_ms   | INTEGER | UTC ms закрытия (NULL если открыта)     |
| symbol        | TEXT    | пара/символ                             |
| exchange      | TEXT    | биржа                                   |
| interval      | TEXT    | интервал стратегии                      |
| entry_price   | REAL    | цена входа                              |
| exit_price    | REAL    | цена выхода                             |
| base_qty      | REAL    | количество базового актива              |
| quote_spent   | REAL    | потрачено котируемого                   |
| is_open       | INTEGER | 1/0 открыт ли                           |
| meta_json     | TEXT    | JSON‑метаданные                         |

Индексы:  
- `INDEX trades_dry_idx_open ON trades_dry(is_open, ts_open_ms DESC)`

---

## Таблица: `trades_live`
Реальные сделки (LIVE).

Структура аналогична `trades_dry`.

Индексы:  
- `INDEX trades_live_idx_open ON trades_live(is_open, ts_open_ms DESC)`

---

## Таблица: `wallet`
Срез доступных средств по активам.

**PK:** `(asset)`

| колонка    | тип     | описание                  |
|------------|---------|---------------------------|
| asset      | TEXT    | тикер актива (USDC и т.п.)|
| free       | REAL    | доступно                  |
| locked     | REAL    | заблокировано             |
| updated_ms | INTEGER | UTC ms последнего апдейта |

---

## Таблица: `orders_live` (опционально)
Хранение ордеров биржи в LIVE.

| колонка           | тип     | описание                |
|-------------------|---------|-------------------------|
| exchange_order_id | TEXT    | PK (уникальный id)     |
| symbol            | TEXT    |                        |
| qty               | REAL    |                        |
| price             | REAL    |                        |
| side              | TEXT    | BUY/SELL               |
| status            | TEXT    | NEW/FILLED/CANCELED... |
| ts_ms             | INTEGER | UTC ms                 |

**PK/UNIQUE:** `exchange_order_id`

---

## Замечания по консистентности
- DRY‑сделки **только** в `trades_dry`; LIVE — **только** в `trades_live`.
- Все вычисления и хранение времени — **UTC (ms)**. Конвертация в локальные зоны — только на вывод.
- `candles` — единая таблица для всех интервалов; интервал задаётся в поле `interval`.

## Расположение БД
- По умолчанию (если `DB_URL=None`) путь собирается как `DATA_DIR/ebot.db`, где `DATA_DIR=./data`.  
- Итоговый файл SQLite: **`data/ebot.db`**.

