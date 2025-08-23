# -*- coding: utf-8 -*-
import time
from sqlalchemy import select
from .base import session_scope
from .models import Wallet
import config as cfg

def ensure_start_balance():
    base_quote = cfg.TRADE.get("BASE_QUOTE", "USDC")
    start_amt = float(getattr(cfg, "DRY_USDC_START", 1000.0))
    now = int(time.time()*1000)
    with session_scope() as s:
        w = s.get(Wallet, base_quote)
        if not w:
            s.add(Wallet(asset=base_quote, free=start_amt, locked=0.0, updated_ms=now))

def get_free(asset: str) -> float:
    with session_scope() as s:
        w = s.get(Wallet, asset)
        return 0.0 if not w else float(w.free)

def add_free(asset: str, delta: float) -> None:
    now = int(time.time()*1000)
    with session_scope() as s:
        w = s.get(Wallet, asset)
        if not w:
            w = Wallet(asset=asset, free=0.0, locked=0.0, updated_ms=now)
            s.add(w)
        w.free = float(w.free) + float(delta)
        w.updated_ms = now
