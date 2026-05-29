"""
技术指标计算工具。
基于 Pandas/NumPy 实现常用技术指标计算。

预留供 M03 预警引擎和 M02 行情模块使用。
"""

from typing import List, Optional
import numpy as np
import pandas as pd


def calc_ma(prices: List[float], period: int) -> List[Optional[float]]:
    """计算移动平均线 (MA)"""
    if len(prices) < period:
        return [None] * len(prices)
    series = pd.Series(prices)
    ma = series.rolling(window=period).mean()
    return [None if pd.isna(v) else round(v, 2) for v in ma.tolist()]


def calc_ema(prices: List[float], period: int) -> List[Optional[float]]:
    """计算指数移动平均线 (EMA)"""
    if len(prices) < period:
        return [None] * len(prices)
    series = pd.Series(prices)
    ema = series.ewm(span=period, adjust=False).mean()
    return [None if pd.isna(v) else round(v, 2) for v in ema.tolist()]


def calc_macd(
    prices: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict:
    """
    计算 MACD 指标。
    返回: {"dif": [], "dea": [], "macd_histogram": []}
    """
    if len(prices) < slow + signal:
        return {"dif": [], "dea": [], "macd_histogram": []}

    series = pd.Series(prices)
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = 2 * (dif - dea)

    return {
        "dif": [round(v, 4) for v in dif.tolist()],
        "dea": [round(v, 4) for v in dea.tolist()],
        "macd_histogram": [round(v, 4) for v in macd_hist.tolist()],
    }


def calc_kdj(
    high: List[float],
    low: List[float],
    close: List[float],
    period: int = 9,
    k_period: int = 3,
    d_period: int = 3,
) -> dict:
    """计算 KDJ 指标"""
    n = len(close)
    if n < period:
        return {"k": [], "d": [], "j": []}

    lowest_low = pd.Series(low).rolling(window=period).min()
    highest_high = pd.Series(high).rolling(window=period).max()
    rsv = (pd.Series(close) - lowest_low) / (highest_high - lowest_low) * 100

    k_vals = []
    d_vals = []
    prev_k = 50.0
    prev_d = 50.0
    for v in rsv:
        if pd.isna(v):
            k_vals.append(None)
            d_vals.append(None)
            continue
        curr_k = (2 / 3) * prev_k + (1 / 3) * v
        curr_d = (2 / 3) * prev_d + (1 / 3) * curr_k
        k_vals.append(round(curr_k, 2))
        d_vals.append(round(curr_d, 2))
        prev_k = curr_k
        prev_d = curr_d

    j_vals = [
        round(3 * k - 2 * d, 2) if k is not None and d is not None else None
        for k, d in zip(k_vals, d_vals)
    ]

    return {"k": k_vals, "d": d_vals, "j": j_vals}


def calc_rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
    """计算 RSI 指标"""
    if len(prices) < period + 1:
        return [None] * len(prices)

    series = pd.Series(prices)
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return [None if pd.isna(v) else round(v, 2) for v in rsi.tolist()]
