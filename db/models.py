# -*- coding: utf-8 -*-
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, BigInteger, Boolean, JSON

Base = declarative_base()

class Candle(Base):
    __tablename__ = "candles"
    pair = Column(String(40), primary_key=True)
    exchange = Column(String(20), primary_key=True)
    interval = Column(String(10), primary_key=True)
    ts_ms = Column(BigInteger, primary_key=True)
    open = Column(Float); high = Column(Float); low = Column(Float); close = Column(Float); volume = Column(Float)

class CurrentPrice(Base):
    __tablename__ = "current_price"
    ts_ms = Column(BigInteger, primary_key=True)
    current_median = Column(Float)
    mexc_mid = Column(Float); binance_mid = Column(Float); bybit_mid = Column(Float)
    usdc_usdt_rate = Column(Float)
    mode = Column(String(20)); sources_count = Column(Integer)

class TradeDry(Base):
    __tablename__ = "trades_dry"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_open_ms = Column(BigInteger); ts_close_ms = Column(BigInteger)
    symbol = Column(String(40)); exchange = Column(String(20)); interval = Column(String(10))
    entry_price = Column(Float); exit_price = Column(Float)
    base_qty = Column(Float); quote_spent = Column(Float)
    is_open = Column(Boolean, default=True)
    meta_json = Column(JSON)

class TradeLive(Base):
    __tablename__ = "trades_live"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_open_ms = Column(BigInteger); ts_close_ms = Column(BigInteger)
    symbol = Column(String(40)); exchange = Column(String(20)); interval = Column(String(10))
    entry_price = Column(Float); exit_price = Column(Float)
    base_qty = Column(Float); quote_spent = Column(Float)
    is_open = Column(Boolean, default=True)
    meta_json = Column(JSON)

class Wallet(Base):
    __tablename__ = "wallet"
    asset = Column(String(20), primary_key=True)
    free = Column(Float, default=0.0)
    locked = Column(Float, default=0.0)
    updated_ms = Column(BigInteger)

class OrderLive(Base):
    __tablename__ = "orders_live"
    exchange_order_id = Column(String(64), primary_key=True)
    symbol = Column(String(40)); qty = Column(Float); price = Column(Float)
    side = Column(String(4)); status = Column(String(20)); ts_ms = Column(BigInteger)
