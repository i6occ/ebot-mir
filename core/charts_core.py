# -*- coding: utf-8 -*-
# Свечи (mplfinance), MSK-время, EMA9/20, MID=(H+L+C)/3 сглаженная EMA.
# Стрелки: потенциальный вход (зелёная ↑) и ближайший последующий выход (красная ↓) по кроссам EMA.
# Буквы B/S: фактически исполненные сделки (из БД), без ценников.

from __future__ import annotations
from typing import List, Tuple, Optional
from datetime import timezone, timedelta

import numpy as np
import pandas as pd
import pytz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import mplfinance as mpf

from db.base import session_scope
from db.models import Candle, CurrentPrice, TradeDry, TradeLive
import config as cfg

MSK = pytz.timezone("Europe/Moscow")

# ---------------- EMA / helpers
def _ema(arr: List[float], period: int) -> List[float]:
    if not arr:
        return []
    if period <= 1:
        return list(arr)
    a = 2.0 / (period + 1.0)
    out = [arr[0]]
    for x in arr[1:]:
        out.append(a * x + (1.0 - a) * out[-1])
    return out

def _interval_seconds(interval: str) -> int:
    iv = (interval or "1m").strip().lower()
    if iv.endswith("m"): return max(1, int(iv[:-1])) * 60
    if iv.endswith("h"): return max(1, int(iv[:-1])) * 3600
    if iv.endswith("d"): return max(1, int(iv[:-1])) * 86400
    return 60

# ---------------- DB loaders (плоские кортежи, без Detached)
def load_candles_flat(symbol: str, exchange: str, interval: str, limit: int):
    with session_scope() as s:
        q = (s.query(Candle.ts_ms, Candle.open, Candle.high, Candle.low, Candle.close, Candle.volume)
               .filter(Candle.pair==symbol, Candle.exchange==exchange, Candle.interval==interval)
               .order_by(Candle.ts_ms.desc())
               .limit(limit))
        rows = list(reversed(q.all()))
    return [(int(ts), float(o), float(h), float(l), float(c), float(volume or 0.0)) for ts,o,h,l,c,volume in rows]

def load_executed_trades(symbol: str, exchange: str, interval: str, limit: int = 100):
    # DRY/LIVE выбираем по cfg.DRY_RUN
    mode_dry = bool(getattr(cfg, "DRY_RUN", True))
    Model = TradeDry if mode_dry else TradeLive
    out=[]
    with session_scope() as s:
        rows = (s.query(Model)
                  .filter(Model.symbol==symbol, Model.exchange==exchange, Model.interval==interval)
                  .order_by(Model.id.desc())
                  .limit(limit)
                  .all())
        for t in rows:
            out.append(dict(
                open_ms=int(t.ts_open_ms or 0),
                close_ms=int(t.ts_close_ms or 0),
                is_open=bool(t.is_open),
            ))
    out.sort(key=lambda x: x["open_ms"])
    return out

# ---------------- signals: EMA crosses
def find_cross_points(ema_f: List[float], ema_s: List[float],
                      entry_min_gap_pct: float, cross_grace_bars: int) -> Tuple[List[int], List[int]]:
    n = min(len(ema_f), len(ema_s))
    buy_idx, sell_idx = [], []
    up_flag = 0
    dn_flag = 0
    for i in range(1, n):
        f0, s0 = ema_f[i-1], ema_s[i-1]
        f1, s1 = ema_f[i],   ema_s[i]
        # фиксируем факт кросса
        if f0 < s0 and f1 >= s1:
            up_flag = max(1, int(cross_grace_bars))
        if f0 > s0 and f1 <= s1:
            dn_flag = max(1, int(cross_grace_bars))
        # зазор
        if up_flag > 0 and f1 >= s1 * (1.0 + entry_min_gap_pct):
            buy_idx.append(i); up_flag = 0
        elif up_flag > 0:
            up_flag -= 1
        if dn_flag > 0 and f1 <= s1 * (1.0 - entry_min_gap_pct):
            sell_idx.append(i); dn_flag = 0
        elif dn_flag > 0:
            dn_flag -= 1
    return buy_idx, sell_idx

def pair_crosses(buy_idx: List[int], sell_idx: List[int]) -> List[Tuple[int,int]]:
    """К каждому BUY — ближайший следующий SELL."""
    pairs=[]; si=0
    for b in buy_idx:
        while si < len(sell_idx) and sell_idx[si] <= b:
            si += 1
        if si < len(sell_idx):
            pairs.append((b, sell_idx[si]))
            si += 1
    return pairs

# ---------------- map ms -> index
def map_ms_to_index(idx: pd.DatetimeIndex, ms: int) -> Optional[int]:
    if not ms or len(idx) == 0:
        return None
    target = pd.to_datetime(ms, unit="ms", utc=True).tz_convert(MSK)
    # ищем ближайший индекс по времени
    deltas = np.abs((idx - target).astype("timedelta64[ms]").astype(np.int64))
    pos = int(np.argmin(deltas))
    return pos

# ---------------- main
def make_candles_png(symbol: str, exchange: str, interval: str, out_path: str,
                     n: int = 60, ema_fast: int = 9, ema_slow: int = 20,
                     mid_smooth: int = 9, legend_loc: str = "upper left") -> Tuple[Optional[str], list]:
    rows = load_candles_flat(symbol, exchange, interval, limit=max(n, 180))
    if not rows:
        return None, []

    ts  = [r[0] for r in rows][-n:]
    op  = [r[1] for r in rows][-n:]
    hi  = [r[2] for r in rows][-n:]
    lo  = [r[3] for r in rows][-n:]
    cl  = [r[4] for r in rows][-n:]
    vol = [r[5] for r in rows][-n:]

    # DataFrame для mplfinance (MSK)
    idx = pd.to_datetime(ts, unit="ms", utc=True).tz_convert(MSK)
    df = pd.DataFrame({"Open":op, "High":hi, "Low":lo, "Close":cl, "Volume":vol}, index=idx)

    # EMA
    ema_f = _ema(cl, max(2, int(ema_fast)))
    ema_s = _ema(cl, max(2, int(ema_slow)))

    # MID = (H+L+C)/3, сглаженная EMA(mid_smooth)
    mid_raw = (np.array(hi) + np.array(lo) + np.array(cl)) / 3.0
    if mid_smooth and mid_smooth > 1:
        a = 2.0/(mid_smooth+1.0)
        mid_sm = [float(mid_raw[0])]
        for x in mid_raw[1:]:
            mid_sm.append(a*float(x) + (1.0-a)*mid_sm[-1])
        mid_series = pd.Series(mid_sm, index=idx, name="MID")
    else:
        mid_series = pd.Series(mid_raw, index=idx, name="MID")

    # Потенциальные сигналы: кроссы EMA -> пары B->S (стрелки)
    gap   = float(cfg.STRATEGY.get("ENTRY_MIN_GAP_PCT", 0.0005))
    grace = int(cfg.STRATEGY.get("CROSS_GRACE_BARS", 3))
    buy_i, sell_i = find_cross_points(ema_f, ema_s, gap, grace)
    pairs_bs = pair_crosses(buy_i, sell_i)

    # Реальные сделки для букв B/S
    trades = load_executed_trades(symbol, exchange, interval, limit=100)

    # Стиль графика
    style = mpf.make_mpf_style(base_mpf_style="nightclouds", gridstyle="--")

    # Доп. линии (EMA/MID)
    ap = [
        mpf.make_addplot(ema_f, color="#4aa3ff", width=1.8),
        mpf.make_addplot(ema_s, color="#ffb04a", width=1.8),
        mpf.make_addplot(mid_series.values, color="#d3d3d3", width=1.3),
    ]

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        addplot=ap,
        returnfig=True,
        volume=False,
        figsize=(14,5),
        tight_layout=True,
        datetime_format="%H:%M",
        xrotation=0,
    )
    ax = axes[0]

    # Стрелки (потенциальные вход/выход без ценников)
    for b, s_i in pairs_bs:
        if 0 <= b < len(idx):
            ax.scatter(idx[b], df["Close"].iloc[b], marker="^", s=70, color="#2ecc71", zorder=5)
        if 0 <= s_i < len(idx):
            ax.scatter(idx[s_i], df["Close"].iloc[s_i], marker="v", s=70, color="#e74c3c", zorder=5)

    # Буквы B/S (факт сделок): у low/high свечи
    for tr in trades:
        io = map_ms_to_index(idx, tr["open_ms"])
        ic = map_ms_to_index(idx, tr["close_ms"]) if tr.get("close_ms") else None
        if io is not None and 0 <= io < len(idx):
            ax.text(idx[io], df["Low"].iloc[io]*0.999, "B",
                    color="#2ecc71", fontsize=9, ha="center", va="top", fontweight="bold")
        if ic is not None and 0 <= ic < len(idx):
            ax.text(idx[ic], df["High"].iloc[ic]*1.001, "S",
                    color="#e74c3c", fontsize=9, ha="center", va="bottom", fontweight="bold")

    # Заголовок (MSK)
    title_mid = float(mid_series.iloc[-1])
    ax.set_title(f"{symbol} @ {exchange} ({interval})   MID={title_mid:.2f}  •  {idx[-1].strftime('%Y-%m-%d %H:%M:%S %Z')}",
                 pad=10)

    # Легенда внизу по центру
    legend_handles = [
        Line2D([0],[0], color="#4aa3ff", lw=1.8, label=f"EMA{ema_fast}"),
        Line2D([0],[0], color="#ffb04a", lw=1.8, label=f"EMA{ema_slow}"),
        Line2D([0],[0], color="#d3d3d3", lw=1.3, label="MID"),
    ]
    ax.legend(handles=legend_handles, loc='lower center', ncol=3,
              bbox_to_anchor=(0.5, -0.22), frameon=False)

    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return out_path, []
