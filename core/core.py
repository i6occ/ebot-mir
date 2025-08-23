# -*- coding: utf-8 -*-
def _ema_seq(values, period):
    if period <= 0 or len(values) < period: return []
    k = 2.0 / (period + 1.0)
    ema = values[0]
    out = [ema]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
        out.append(ema)
    return out

def compute_signal(closes, price_now, ema_fast=9, ema_slow=20, entry_min_gap_pct=0.0005, cross_grace_bars=3):
    """Возвращает (signal, meta).
    Вход: BUY если cross_up подтверждён на i-1 и на текущем live-bar i: EMA9>EMA20 и gap>=N,
    причём допускается «память кросса» на следующие 3 закрытых бара.
    Выход: SELL при EMA20>=EMA9 на live-bar i.
    """
    n = max(ema_fast, ema_slow) * 3
    if len(closes) < n: 
        return "HOLD", {"reason":"not_enough_bars", "need": n, "have": len(closes)}
    arr = closes[-n:]
    f = _ema_seq(arr, ema_fast)
    s = _ema_seq(arr, ema_slow)
    if len(f) != len(s): 
        m = min(len(f), len(s)); f, s = f[-m:], s[-m:]
    k = len(f) - 1  # индекс текущего (live) значения
    if k < 2:
        return "HOLD", {"reason":"short_seq"}

    # индексы: k -> i (live), k-1 -> i-1 (закрыт), k-2 -> i-2 (закрыт)
    ema9_i2, ema20_i2 = f[k-2], s[k-2]
    ema9_i1, ema20_i1 = f[k-1], s[k-1]
    ema9_i , ema20_i  = f[k],   s[k]

    cross_up_i1 = (ema9_i2 < ema20_i2) and (ema9_i1 >= ema20_i1)
    ema_up_i    = (ema9_i  >  ema20_i )
    gap_i       = (ema9_i - ema20_i) / float(price_now or 1.0)

    # если нет прямого cross_up@i-1, проверим «последний кросс вверх» не старше grace
    def last_cross_up_index():
        # по закрытым: рассматриваем k-1, k-2, k-3 ...
        for off in range(1, cross_grace_bars+2):  # +2 чтобы покрыть i-1 и ещё 2-3
            j = k - off
            if j-1 >= 0:
                if (f[j-1] < s[j-1]) and (f[j] >= s[j]):
                    return j
        return None

    lcu = (k-1) if cross_up_i1 else last_cross_up_index()
    cross_window_ok = (lcu is not None) and ((k - lcu) <= cross_grace_bars)

    if ema9_i <= ema20_i:
        return "SELL", {"reason":"cross_down_live", "ema9":ema9_i, "ema20":ema20_i}

    if cross_window_ok and ema_up_i and gap_i >= float(entry_min_gap_pct):
        return "BUY", {"reason":"cross_up+gap", "gap":gap_i, "ema9":ema9_i, "ema20":ema20_i, "lcu":lcu, "grace":cross_grace_bars}

    return "HOLD", {"reason":"no_entry", "ema9":ema9_i, "ema20":ema20_i, "gap":gap_i, "lcu":lcu}
