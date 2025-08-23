# VARIABLES (словарь проекта)

## CONFIG (ключи и смысл)
- DRY_RUN: bool — режим: True=симуляция, False=LIVE.
- DATA_DIR/LOGS_DIR/CACHE_DIR/TMP_DIR/PAIRS_DIR: str — пути.
- TRADE_COOLDOWN_SEC: float — пауза между итерациями.
- DRY_USDC_START: float — стартовый USDC для DRY.
- DB_URL: str|None — если None → SQLite ebot.db; иначе DSN PostgreSQL.
- TELEGRAM: {ENABLED, BOT_TOKEN, CHAT_ID} — настройки чата.
- TRADE: { BASE_QUOTE, ALLOC_MODE, ALLOC_PCT, MIN_NOTIONAL_USD, ORDER_TYPE, SLIPPAGE_BPS }
- EXCHANGES.MEXC: { API_KEY, API_SECRET, BASE_URL, RECV_WINDOW_MS, HTTP_TIMEOUT_SEC, WS_PUBLIC_URL, ENDPOINTS, SYMBOL_RULES }
- STRATEGY: { PAIRS:[{symbol,exchange,interval}], EMA_FAST, EMA_SLOW, GAP_THRESHOLD_BPS }
  - GAP_THRESHOLD_BPS: int — минимальное расхождение EMA в базисных пунктах (1/100 процента), при превышении которого сигнал считается действительным.
- CANDLES: { PAIRS, LOOKBACK_BARS, SAFETY_MS, RETRY_MAX, RETRY_SLEEP, TIMEOUT, SLEEP_BETWEEN, CHUNK }
- CURRENT_PRICE: { ENABLE_TRACKING, ENABLE_USE, DIVERGENCE_BPS, WINDOW_SEC, RETENTION_HOURS, USDCUSDT_POLL_SEC, SOURCES, SYMBOLS, PRIMARY_EXCHANGE, USE_WEBSOCKETS }
- REPORTS: { ENABLED, FREQUENCY_MIN, PAIRS, SEND_CHARTS, INLINE_TEXT }
- LOGGING: { LEVEL, TO_FILE, FILE, ROTATE_MB, BACKUP_COUNT }

## DB: таблицы (минимальный набор)
### candles
- PK: (pair, exchange, interval, ts_ms)
- cols: open, high, low, close, volume

### current_price
- ts_ms, current_median, mexc_mid, binance_mid, bybit_mid, usdc_usdt_rate, mode, sources_count

### trades_dry / trades_live
- id, ts_open_ms, ts_close_ms, symbol, exchange, interval,
  entry_price, exit_price, base_qty, quote_spent, is_open, meta_json

### wallet
- asset (PK), free, locked, updated_ms

### orders_live (опционально)
- exchange_order_id, symbol, qty, price, side, status, ts_ms

### signals (опционально)
- ts_ms, symbol, exchange, interval, ema_fast, ema_slow, gap_bps, decision, reason

> Любое изменение схемы фиксируем миграцией в db/migrations и дополняем этот файл.
