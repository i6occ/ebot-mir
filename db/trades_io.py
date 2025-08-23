# -*- coding: utf-8 -*-
import time
from sqlalchemy import select
from .base import session_scope
from .models import TradeDry, TradeLive
import config as cfg

def _tab():
    return TradeDry if getattr(cfg, "DRY_RUN", True) else TradeLive

def has_open(symbol: str, exchange: str, interval: str) -> bool:
    with session_scope() as s:
        q = s.execute(
            select(_tab()).where(
                _tab().symbol == symbol,
                _tab().exchange == exchange,
                _tab().interval == interval,
                _tab().is_open == True
            ).limit(1)
        ).scalars().first()
        return q is not None

def open_entry(symbol: str, exchange: str, interval: str,
               entry_price: float, base_qty: float, quote_spent: float = 0.0, meta=None) -> None:
    with session_scope() as s:
        t = _tab()(
            ts_open_ms=int(time.time()*1000),
            ts_close_ms=None,
            symbol=symbol, exchange=exchange, interval=interval,
            entry_price=float(entry_price), exit_price=None,
            base_qty=float(base_qty), quote_spent=float(quote_spent),
            is_open=True, meta_json=(meta or {})
        )
        s.add(t)

def close_entry(symbol: str, exchange: str, interval: str,
                exit_price: float, meta=None) -> bool:
    with session_scope() as s:
        q = s.execute(
            select(_tab()).where(
                _tab().symbol == symbol,
                _tab().exchange == exchange,
                _tab().interval == interval,
                _tab().is_open == True
            ).limit(1)
        ).scalars().first()
        if not q:
            return False
        q.exit_price = float(exit_price)
        q.ts_close_ms = int(time.time()*1000)
        q.is_open = False
        if meta:
            q.meta_json = {**(q.meta_json or {}), **meta}
        s.add(q)
        return True


def get_open(symbol: str, exchange: str, interval: str):
    from sqlalchemy import select
    with session_scope() as s_:
        return s_.execute(
            select(_tab()).where(
                _tab().symbol==symbol,
                _tab().exchange==exchange,
                _tab().interval==interval,
                _tab().is_open==True
            ).limit(1)
        ).scalars().first()
