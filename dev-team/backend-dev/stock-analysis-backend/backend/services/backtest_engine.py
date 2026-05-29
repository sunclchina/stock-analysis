"""
资产组合回测引擎 — 基于策略配置模拟逐日交易。

职责：
1. 读取策略 config_json（买入/卖出/加仓/减仓/风控/止盈止损）
2. 从数据源获取历史K线（支持复权）
3. 逐日模拟：信号判定 → 交易执行 → 持仓更新
4. 计算绩效指标：累计收益/年化/最大回撤/胜率/盈亏比
5. 手续费/印花税/滑点 模型
"""

import logging
import math
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)

# ─── 交易成本配置 ───
DEFAULT_COMMISSION_RATE = 0.00025   # 万分之2.5
DEFAULT_STAMP_TAX_RATE = 0.001      # 千分之1（仅卖出）
DEFAULT_SLIPPAGE_RATE = 0.0005      # 万分之5（百分比模式）
MIN_COMMISSION = 5.0                # 最低手续费 5 元

# ─── 价格模式 ───
BUY_PRICE_MODE = "close"  # 开盘/收盘/指定时间
SELL_PRICE_MODE = "close"

# ─── K线数据结构 ───
class Bar:
    __slots__ = ("date", "open", "high", "low", "close", "volume", "amount")
    def __init__(self, date, open, high, low, close, volume=0, amount=0):
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount


# ═══════════════════════════════════════════════════
# 1. 技术指标计算
# ═══════════════════════════════════════════════════

class Indicators:
    """根据收盘价序列计算常用技术指标"""

    @staticmethod
    def sma(prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return [None] * len(prices)
        result = []
        cum = sum(prices[:period])
        result.append(cum / period)
        for i in range(period, len(prices)):
            cum = cum - prices[i - period] + prices[i]
            result.append(cum / period)
        return [None] * (period - 1) + result

    @staticmethod
    def ema(prices: List[float], period: int) -> List[float]:
        if len(prices) < period:
            return [None] * len(prices)
        multiplier = 2.0 / (period + 1)
        result = [None] * (period - 1)
        result.append(sum(prices[:period]) / period)
        for i in range(period, len(prices)):
            result.append((prices[i] - result[-1]) * multiplier + result[-1])
        return result

    @staticmethod
    def macd(prices: List[float], fast=12, slow=26, signal=9):
        ema_fast = Indicators.ema(prices, fast)
        ema_slow = Indicators.ema(prices, slow)
        dif = [(f - s) if f is not None and s is not None else None
               for f, s in zip(ema_fast, ema_slow)]
        # dea = ema of dif
        valid_dif = [v for v in dif if v is not None]
        if not valid_dif:
            return [None] * len(prices), [None] * len(prices)
        dea_list = [None] * (len(dif) - len(valid_dif))
        dea_vals = Indicators.ema(valid_dif, signal)
        dea_list.extend(dea_vals)
        histogram = [(d - dea) if d is not None and dea is not None else None
                     for d, dea in zip(dif, dea_list)]
        return dif, dea_list, histogram

    @staticmethod
    def rsi(prices: List[float], period=14) -> List[float]:
        if len(prices) <= period:
            return [None] * len(prices)
        result = [None] * (period)
        gains, losses = 0, 0
        for i in range(1, period + 1):
            diff = prices[i] - prices[i - 1]
            if diff > 0: gains += diff
            else: losses -= diff
        avg_gain = gains / period
        avg_loss = losses / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        result.append(100 - 100 / (1 + rs))
        for i in range(period + 1, len(prices)):
            diff = prices[i] - prices[i - 1]
            gain = diff if diff > 0 else 0
            loss = -diff if diff < 0 else 0
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            result.append(100 - 100 / (1 + rs))
        return result

    @staticmethod
    def kdj(bars: List[Bar], period=9, k_smooth=3, d_smooth=3):
        """KDJ 计算"""
        n = len(bars)
        k_vals, d_vals, j_vals = [], [], []
        for i in range(n):
            if i < period - 1:
                k_vals.append(None); d_vals.append(None); j_vals.append(None)
                continue
            hh = max(b.high for b in bars[max(0, i - period + 1):i + 1])
            ll = min(b.low for b in bars[max(0, i - period + 1):i + 1])
            close = bars[i].close
            rsv = (close - ll) / (hh - ll) * 100 if hh != ll else 50
            if i == period - 1:
                k = rsv
                d = rsv
            else:
                k = 2/3 * k_vals[-1] + 1/3 * rsv
                d = 2/3 * d_vals[-1] + 1/3 * k
            j = 3 * k - 2 * d
            k_vals.append(k); d_vals.append(d); j_vals.append(j)
        return k_vals, d_vals, j_vals

    @staticmethod
    def ma_direction(prices: List[float], short=5, medium=10, long=20):
        """均线排列方向：1=多头, -1=空头, 0=缠绕"""
        ma5 = Indicators.sma(prices, short)
        ma10 = Indicators.sma(prices, medium)
        ma20 = Indicators.sma(prices, long)
        direction = []
        for i in range(len(prices)):
            m5, m10, m20 = ma5[i], ma10[i], ma20[i]
            if m5 is None or m10 is None or m20 is None:
                direction.append(0)
            elif m5 > m10 > m20: direction.append(1)     # 多头排列
            elif m5 < m10 < m20: direction.append(-1)    # 空头排列
            else: direction.append(0)
        return direction

    @staticmethod
    def volume_break(volumes: List[float], period=20, ratio=1.5):
        """放量突破判断：成交量 > 均量 × ratio"""
        if len(volumes) <= period:
            return [False] * len(volumes)
        result = [False] * period
        for i in range(period, len(volumes)):
            avg_vol = sum(volumes[i - period:i]) / period
            result.append(volumes[i] > avg_vol * ratio)
        return result


# ═══════════════════════════════════════════════════
# 2. 策略信号评估
# ═══════════════════════════════════════════════════

class SignalEvaluator:
    """根据策略配置和当前技术指标评估买卖信号"""

    @staticmethod
    def eval_buy_signal(cfg: dict, bars: List[Bar], idx: int, indicators: dict) -> bool:
        """评估买入信号"""
        buy_rules = cfg.get("buy_rules", {})
        if not buy_rules.get("enabled", False):
            return False

        price = bars[idx].close
        prices = [b.close for b in bars]
        volumes = [b.volume for b in bars]

        # 趋势条件
        if buy_rules.get("trend_up") or buy_rules.get("trend_reversal"):
            ma_dir = indicators["ma_direction"]
            if buy_rules.get("trend_up") and ma_dir[idx] == 1:
                pass
            elif buy_rules.get("trend_reversal") and ma_dir[max(0, idx - 5)] < 0 and ma_dir[idx] >= 0:
                pass
            else:
                return False

        # 排除震荡/下跌
        if buy_rules.get("excl_oscillate") and indicators["ma_direction"][idx] == 0:
            return False
        if buy_rules.get("excl_down") and indicators["ma_direction"][idx] == -1:
            return False

        # 技术指标条件
        macd_dif, macd_dea, macd_hist = indicators["macd"]
        k_val, d_val, j_val = indicators["kdj"]
        rsi_vals = indicators["rsi"]

        # MA20站稳
        if buy_rules.get("ma20_stand"):
            ma20 = indicators["ma20"][idx]
            if ma20 is None or price < ma20 * 0.98:
                return False

        # 均线多头排列
        if buy_rules.get("ma_multi_up") and indicators["ma_direction"][idx] != 1:
            return False

        # MACD金叉
        if buy_rules.get("macd_golden"):
            if idx < 1 or macd_hist[idx] is None or macd_hist[idx - 1] is None:
                return False
            if not (macd_hist[idx - 1] <= 0 < macd_hist[idx]):
                return False

        # MACD红柱扩大
        if buy_rules.get("macd_red_expand"):
            if idx < 1 or macd_hist[idx] is None or macd_hist[idx - 1] is None:
                return False
            if not (macd_hist[idx] > 0 and macd_hist[idx] > macd_hist[idx - 1]):
                return False

        # KDJ低位金叉
        if buy_rules.get("kdj_golden"):
            if k_val[idx] is None or d_val[idx] is None:
                return False
            if idx > 0 and k_val[idx - 1] is not None and d_val[idx - 1] is not None:
                if not (k_val[idx - 1] < d_val[idx - 1] and k_val[idx] > d_val[idx] and k_val[idx] < 40):
                    return False
            else:
                return False

        # RSI低位向上
        if buy_rules.get("rsi_up"):
            if rsi_vals[idx] is None:
                return False
            if idx > 0 and rsi_vals[idx - 1] is not None:
                if not (rsi_vals[idx - 1] < 40 < rsi_vals[idx]):
                    return False
            else:
                return False

        # 放量突破
        if buy_rules.get("volume_break"):
            vol_break = Indicators.volume_break(volumes, 20, 1.5)
            if not vol_break[idx]:
                return False

        # 多头共振
        if buy_rules.get("resonance", {}).get("enabled"):
            threshold = buy_rules["resonance"].get("count", 3)
            count = 0
            if buy_rules.get("ma_multi_up") or indicators["ma_direction"][idx] == 1: count += 1
            if idx > 0 and macd_hist[idx] is not None and macd_hist[idx] > (macd_hist[idx-1] or 0): count += 1
            if rsi_vals[idx] is not None and rsi_vals[idx] > 50: count += 1
            if count < threshold: return False

        # 风险评分
        if buy_rules.get("risk_score", {}).get("enabled"):
            max_score = buy_rules["risk_score"].get("max", 30)
            # 简化的风险评分：基于RSI和均线位置
            if rsi_vals[idx] is not None and rsi_vals[idx] > 70:
                return False  # 超买区

        # 排除ST（简化：检查价格是否异常）
        if buy_rules.get("excl_st") and price < 0.5:
            return False

        return True

    @staticmethod
    def eval_sell_signal(cfg: dict, bars: List[Bar], idx: int, indicators: dict,
                         buy_price: float, days_held: int) -> bool:
        """评估卖出信号"""
        sell_rules = cfg.get("sell_rules", {})
        if not sell_rules.get("enabled", False):
            return False

        price = bars[idx].close
        prices = [b.close for b in bars]
        ma_dir = indicators["ma_direction"]
        macd_dif, macd_dea, macd_hist = indicators["macd"]
        rsi_vals = indicators["rsi"]

        # 趋势破位
        if sell_rules.get("trend_turn") and ma_dir[idx] != -1:  # 只要不是空头就不算趋势破位，但需要更精细
            if not (ma_dir[max(0, idx - 3)] >= 0 and ma_dir[idx] <= 0):
                pass  # 趋势转弱

        if sell_rules.get("trend_down") and ma_dir[idx] == -1:
            return True

        if sell_rules.get("break_ma20"):
            ma20 = indicators["ma20"][idx]
            if ma20 is not None and price < ma20:
                return True

        if sell_rules.get("ma_multi_down") and ma_dir[idx] == -1:
            return True

        # 技术信号
        if sell_rules.get("macd_dead"):
            if idx > 0 and macd_hist[idx] is not None and macd_hist[idx - 1] is not None:
                if macd_hist[idx - 1] > 0 >= macd_hist[idx]:
                    return True

        if sell_rules.get("macd_green_expand"):
            if idx > 0 and macd_hist[idx] is not None and macd_hist[idx - 1] is not None:
                if macd_hist[idx] < 0 and macd_hist[idx] < macd_hist[idx - 1]:
                    return True

        if sell_rules.get("rsi_down"):
            if rsi_vals[idx] is not None and rsi_vals[idx] > 70:
                if idx > 0 and rsi_vals[idx - 1] is not None and rsi_vals[idx] < rsi_vals[idx - 1]:
                    return True

        if sell_rules.get("volume_break_weak"):
            volume = bars[idx].volume
            if idx > 5:
                avg_vol = sum(b.volume for b in bars[idx - 5:idx]) / 5
                if volume > avg_vol * 1.5 and price < bars[idx - 1].close:
                    return True

        # 风险与事件（简化）
        if sell_rules.get("bad_news"):
            # 简化为：连续大跌
            if idx >= 3 and all(bars[i].close < bars[i - 1].close for i in range(idx - 2, idx + 1)):
                return True

        return False

    @staticmethod
    def eval_stop(cfg: dict, current_price: float, buy_price: float) -> Optional[str]:
        """评估止盈止损。返回 'profit'/'loss'/None"""
        stop = cfg.get("stop", {})
        pnl_pct = (current_price - buy_price) / buy_price * 100

        if stop.get("profit_enabled") and pnl_pct >= stop.get("profit_pct", 30):
            return "profit"
        if stop.get("loss_enabled") and pnl_pct <= -stop.get("loss_pct", 10):
            return "loss"
        return None


# ═══════════════════════════════════════════════════
# 3. 回测引擎
# ═══════════════════════════════════════════════════

class BacktestEngine:
    """策略回测引擎"""

    def __init__(self, strategy_config: dict, bars: List[Bar],
                 initial_capital: float = 1000000.0,
                 commission_rate: float = DEFAULT_COMMISSION_RATE,
                 stamp_tax_rate: float = DEFAULT_STAMP_TAX_RATE,
                 slippage_rate: float = DEFAULT_SLIPPAGE_RATE):
        self.cfg = strategy_config
        self.bars = bars
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.slippage_rate = slippage_rate

        # 运行时状态
        self.cash = initial_capital
        self.holdings = {}  # code -> {quantity, avg_cost, buy_date}
        self.trades = []    # 交易明细
        self.equity = []    # 每日净值曲线
        self.hold_days = {}  # code -> days since buy

    def _calc_trade_cost(self, amount: float, is_buy: bool) -> float:
        """计算交易费用"""
        commission = max(amount * self.commission_rate, MIN_COMMISSION)
        stamp_tax = amount * self.stamp_tax_rate if not is_buy else 0
        slippage = amount * self.slippage_rate
        return commission + stamp_tax + slippage

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """应用滑点"""
        if is_buy:
            return price * (1 + self.slippage_rate)
        else:
            return price * (1 - self.slippage_rate)

    def run(self) -> Dict[str, Any]:
        """执行回测"""
        n = len(self.bars)
        if n < 20:
            return self._build_error(f"K线数据不足（{n}条），至少需要20条")

        # 预计算所有技术指标
        prices = [b.close for b in self.bars]
        volumes = [b.volume for b in self.bars]

        indicators = {
            "ma5": Indicators.sma(prices, 5),
            "ma10": Indicators.sma(prices, 10),
            "ma20": Indicators.sma(prices, 20),
            "ma60": Indicators.sma(prices, 60),
            "ma_direction": Indicators.ma_direction(prices, 5, 10, 20),
        }
        dif, dea, hist = Indicators.macd(prices)
        indicators["macd"] = (dif, dea, hist)
        indicators["rsi"] = Indicators.rsi(prices, 14)
        k, d, j = Indicators.kdj(self.bars)
        indicators["kdj"] = (k, d, j)

        # 开始位置（需有足够数据计算指标，最少20条）
        min_required = 20
        if n < min_required:
            return self._build_error(f"K线数据不足（{n}条），至少需要{min_required}条")
        warmup = min(n // 2, 60)  # 动态热身长度

        for i in range(warmup, n):
            bar = self.bars[i]
            # 计算当前持仓市值
            has_position = bool(self.holdings)
            position_value = self.holdings["quantity"] * bar.close if has_position else 0

            total_assets = self.cash + position_value
            self.equity.append({
                "date": bar.date,
                "cash": round(self.cash, 2),
                "position_value": round(position_value, 2),
                "total_assets": round(total_assets, 2),
            })

            # 止盈止损检查
            if has_position:
                stop_result = SignalEvaluator.eval_stop(
                    self.cfg, bar.close, self.holdings["buy_price"]
                )
                if stop_result == "profit":
                    self._execute_sell(i, self.holdings["quantity"], bar, "止盈")
                    continue
                elif stop_result == "loss":
                    self._execute_sell(i, self.holdings["quantity"], bar, "止损")
                    continue

            # 卖出/减仓信号
            if has_position:
                days_held = i - self.holdings["buy_idx"]
                sell_signal = SignalEvaluator.eval_sell_signal(
                    self.cfg, self.bars, i, indicators,
                    self.holdings["buy_price"], days_held
                )
                if sell_signal:
                    self._execute_sell(i, self.holdings["quantity"], bar, "卖出信号")
                    continue

            # 买入信号（无持仓时）
            if not has_position:
                buy_signal = SignalEvaluator.eval_buy_signal(
                    self.cfg, self.bars, i, indicators
                )
                if buy_signal:
                    self._execute_buy(i, bar)

        # 最后一日强制清仓
        if bool(self.holdings) and n > warmup:
            last_bar = self.bars[-1]
            self._execute_sell(n - 1, self.holdings["quantity"], last_bar, "到期清仓")

        # 计算结果
        return self._calculate_metrics()

    def _execute_buy(self, idx: int, bar: Bar):
        """执行买入"""
        if not self.cfg.get("buy_rules", {}).get("enabled", False):
            return

        # 仓位风控
        risk = self.cfg.get("risk_control", {})
        max_single_pct = risk.get("single_buy_pct", 100) / 100

        # 计算买入量
        buy_amount = self.cash * max_single_pct
        buy_price = self._apply_slippage(bar.close, is_buy=True)
        quantity = int(buy_amount / buy_price / 100) * 100  # 按100股取整
        if quantity < 100:
            return

        cost = self._calc_trade_cost(buy_amount, is_buy=True)
        actual_amount = quantity * buy_price + cost
        if actual_amount > self.cash:
            # 调整数量
            quantity = int((self.cash - cost) / buy_price / 100) * 100
            if quantity < 100:
                return
            actual_amount = quantity * buy_price + cost

        self.cash -= actual_amount
        avg_cost = (quantity * buy_price + cost) / quantity

        self.holdings = {
            "code": bar.date,  # 用日期作为占位标识
            "quantity": quantity,
            "avg_cost": avg_cost,
            "buy_price": buy_price,
            "total_cost": quantity * buy_price + cost,
            "buy_date": bar.date,
            "buy_idx": idx,
        }

        self.trades.append({
            "date": bar.date,
            "type": "买入",
            "price": round(buy_price, 3),
            "quantity": quantity,
            "amount": round(quantity * buy_price, 2),
            "commission": round(cost, 2),
            "reason": "买入信号",
        })

    def _execute_sell(self, idx: int, quantity: int, bar: Bar, reason: str):
        """执行卖出/清仓"""
        if not self.holdings:
            return

        sell_price = self._apply_slippage(bar.close, is_buy=False)
        amount = quantity * sell_price
        cost = self._calc_trade_cost(amount, is_buy=False)
        net_amount = amount - cost

        # 计算收益
        buy_cost = self.holdings["total_cost"]
        profit = net_amount - buy_cost
        profit_rate = (profit / buy_cost) * 100

        self.cash += net_amount
        self.trades.append({
            "date": bar.date,
            "type": "卖出",
            "price": round(sell_price, 3),
            "quantity": quantity,
            "amount": round(amount, 2),
            "commission": round(cost, 2),
            "profit": round(profit, 2),
            "profit_rate": round(profit_rate, 2),
            "reason": reason,
            "hold_days": idx - self.holdings["buy_idx"],
        })

        self.holdings = {}

    def _calculate_metrics(self) -> Dict[str, Any]:
        """计算绩效指标"""
        n = len(self.equity)
        if n < 2:
            return self._build_error("回测周期太短")

        final_assets = self.equity[-1]["total_assets"]
        total_return = (final_assets - self.initial_capital) / self.initial_capital * 100

        # 年化收益率
        start_date_str = self.equity[0]["date"]
        end_date_str = self.equity[-1]["date"]
        try:
            start = datetime.strptime(str(start_date_str)[:10], "%Y-%m-%d") if isinstance(start_date_str, str) else start_date_str
            end = datetime.strptime(str(end_date_str)[:10], "%Y-%m-%d") if isinstance(end_date_str, str) else end_date_str
            days = (end - start).days if end > start else 1
            years = days / 365.0
            if years > 0:
                annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
            else:
                annual_return = total_return
        except (ValueError, TypeError):
            days = n
            years = n / 245.0  # 约245个交易日/年
            annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0

        # 最大回撤
        peak = self.equity[0]["total_assets"]
        max_drawdown = 0
        for point in self.equity:
            val = point["total_assets"]
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            if dd > max_drawdown:
                max_drawdown = dd

        # 胜率和盈亏比
        win_trades = [t for t in self.trades if t.get("profit", 0) > 0]
        loss_trades = [t for t in self.trades if t.get("profit", 0) < 0]
        total_close_trades = len(win_trades) + len(loss_trades)
        win_rate = len(win_trades) / total_close_trades * 100 if total_close_trades > 0 else 0

        total_win = sum(t["profit"] for t in win_trades) if win_trades else 0
        total_loss = abs(sum(t["profit"] for t in loss_trades)) if loss_trades else 1
        profit_loss_ratio = total_win / total_loss if total_loss > 0 and total_win > 0 else 0

        # 月度收益
        monthly_returns = self._calc_monthly_returns()

        # 交易明细
        buy_trades = [t for t in self.trades if t["type"] == "买入"]
        sell_trades = [t for t in self.trades if t["type"] == "卖出"]

        return {
            "summary": {
                "total_return": round(total_return, 2),
                "annual_return": round(annual_return, 2),
                "max_drawdown": round(max_drawdown, 2),
                "win_rate": round(win_rate, 1),
                "profit_loss_ratio": round(profit_loss_ratio, 2),
                "total_trades": len(buy_trades),
                "total_close_trades": total_close_trades,
                "initial_capital": round(self.initial_capital, 2),
                "final_assets": round(final_assets, 2),
                "commission_rate": self.commission_rate,
                "stamp_tax_rate": self.stamp_tax_rate,
                "slippage_rate": self.slippage_rate,
            },
            "equity_curve": self.equity,
            "trades": self.trades,
            "monthly_returns": monthly_returns,
            "backtest_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "data_range": f"{self.equity[0]['date']} ~ {self.equity[-1]['date']}",
            "days": n,
        }

    def _calc_monthly_returns(self) -> List[Dict]:
        """按月计算收益率"""
        monthly = OrderedDict()
        for point in self.equity:
            d_str = str(point["date"])[:7]  # YYYY-MM
            if d_str not in monthly:
                monthly[d_str] = {"month": d_str, "start": point["total_assets"], "end": point["total_assets"]}
            monthly[d_str]["end"] = point["total_assets"]

        results = []
        prev_end = self.initial_capital
        for month, data in monthly.items():
            ret = (data["end"] - data["start"]) / data["start"] * 100
            results.append({
                "month": month,
                "return": round(ret, 2),
                "return_label": f"{ret:+.2f}%",
            })
            prev_end = data["end"]
        return results

    def _build_error(self, msg: str) -> Dict:
        return {
            "status": "error",
            "error": msg,
            "summary": {},
            "equity_curve": [],
            "trades": [],
            "monthly_returns": [],
        }


# ═══════════════════════════════════════════════════
# 4. 数据获取适配器
# ═══════════════════════════════════════════════════

class KlineDataFetcher:
    """从系统数据源获取历史K线"""

    @staticmethod
    async def _try_fetch(code: str, count: int) -> tuple:
        """尝试从主数据源获取K线，返回 (raw_kline_list, source_name)"""
        from backend.main import data_source_manager as dsm
        klines = await dsm.get_kline(code, count=count)
        if klines:
            return klines, "primary"
        # 检查数据源状态
        try:
            status = dsm.get_status_summary()
            active = [s["name"] for s in status if s.get("is_active")]
            logger.info(f"回测: 主数据源返回空, 可用源={active}")
        except Exception:
            pass
        return [], "primary"

    @staticmethod
    async def _try_fallback(code: str, start_date: str, end_date: str, count: int) -> List[Bar]:
        """备用数据源：通过 sina / baostock + 获取历史K线"""
        import httpx
        bars = []
        try:
            # 尝试新浪免费接口（日K线）
            sina_code = f"sz{code}" if code.startswith(("0", "3", "1")) else f"sh{code}"
            if code.startswith("8") or code.startswith("920"):
                sina_code = f"bj{code}"
            url = f"https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol={sina_code}&scale=240&ma=no&datalen={count}"
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    import json
                    data = json.loads(r.text)
                    if isinstance(data, list):
                        for item in data:
                            d = item.get("date", "")[:10]
                            if not d or d < start_date[:10] or d > end_date[:10]:
                                continue
                            bar = Bar(
                                date=d,
                                open=float(item.get("open", 0)),
                                high=float(item.get("high", 0)),
                                low=float(item.get("low", 0)),
                                close=float(item.get("close", 0)),
                                volume=float(item.get("volume", 0)),
                            )
                            bars.append(bar)
            if bars:
                bars.sort(key=lambda b: b.date)
                logger.info(f"回测备用源(Sina)拉取: {code}, {len(bars)}条")
                return bars
        except Exception as e:
            logger.warning(f"回测备用源(Sina)失败 {code}: {e}")

        # 二次备用：baostack（同步执行）
        try:
            import asyncio
            import baostock as bs
            def _bs_fetch():
                lg = bs.login()
                if lg.error_code != "0":
                    logger.warning(f"baostock login failed: {lg.error_msg}")
                    return []
                try:
                    bs_code = f"{['sh','sz'][code.startswith(('6','9'))]}.{code}"
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        "date,open,high,low,close,volume",
                        start_date=start_date[:10],
                        end_date=end_date[:10],
                        frequency="d",
                        adjustflag="2",  # 后复权
                    )
                    result = []
                    while rs.next():
                        row = rs.get_row_data()
                        if row[1] and row[4]:
                            result.append(Bar(
                                date=row[0],
                                open=float(row[1]),
                                high=float(row[2]),
                                low=float(row[3]),
                                close=float(row[4]),
                                volume=float(row[5]) if row[5] else 0,
                            ))
                    result.sort(key=lambda b: b.date)
                    return result
                finally:
                    bs.logout()
            loop = asyncio.get_event_loop()
            bs_bars = await loop.run_in_executor(None, _bs_fetch)
            if bs_bars:
                logger.info(f"回测备用源(Baostock)拉取: {code}, {len(bs_bars)}条")
                return bs_bars
        except Exception as e:
            logger.warning(f"回测备用源(Baostock)失败 {code}: {e}")

        return []

    @staticmethod
    async def fetch(code: str, start_date: str, end_date: str, count: int = 500) -> List[Bar]:
        """获取K线数据并转为Bar列表

        Args:
            code: 股票代码，如 "000001"
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            count: 最大K线条数（首次尝试后若不足则自动放大）

        Returns:
            List[Bar]: 按日期升序的K线列表
        """
        try:
            # 第一步：主数据源，逐步增加请求量
            attempts = [(count, "初始"), (min(count * 2, 2000), "加倍"), (2000, "最大")]
            all_raw = []
            max_raw_len = 0
            for try_count, label in attempts:
                raw, src = await KlineDataFetcher._try_fetch(code, try_count)
                if len(raw) > max_raw_len:
                    all_raw = raw
                    max_raw_len = len(raw)
                if len(raw) >= 60:
                    logger.info(f"回测数据源: {code}, {label}尝试count={try_count}, 获取{len(raw)}条 ✓")
                    break
                logger.info(f"回测数据源: {code}, {label}尝试count={try_count}, 仅{len(raw)}条，尝试更多")

            klines = all_raw
            if not klines:
                logger.warning(f"回测数据源返回空: {code}")
                # 尝试备用数据源
                logger.info(f"回测: 尝试备用数据源 {code}")
                bars = await KlineDataFetcher._try_fallback(code, start_date, end_date, count)
                return bars

            bars = []
            for k in klines:
                # KLineData 字段: trade_date( datetime), open_price, close_price, high_price, low_price, volume, amount
                if isinstance(k, dict):
                    d = str(k.get("date", k.get("trade_date", "")))[:10]
                    open_p = float(k.get("open", k.get("open_price", 0)))
                    close_p = float(k.get("close", k.get("close_price", 0)))
                    high_p = float(k.get("high", k.get("high_price", 0)))
                    low_p = float(k.get("low", k.get("low_price", 0)))
                    vol = float(k.get("volume", 0))
                else:
                    td = getattr(k, "trade_date", "")
                    if hasattr(td, "strftime"):
                        d = td.strftime("%Y-%m-%d")
                    else:
                        d = str(td)[:10]
                    open_p = float(getattr(k, "open_price", 0))
                    close_p = float(getattr(k, "close_price", 0))
                    high_p = float(getattr(k, "high_price", 0))
                    low_p = float(getattr(k, "low_price", 0))
                    vol = float(getattr(k, "volume", 0))
                if not d or d < "2000-01-01":
                    continue
                # 日期过滤
                if d < start_date[:10] or d > end_date[:10]:
                    continue
                bar = Bar(date=d, open=open_p, high=high_p, low=low_p, close=close_p, volume=vol)
                bars.append(bar)

            # 按日期排序
            bars.sort(key=lambda b: b.date)
            logger.info(f"回测数据拉取: {code} {start_date}~{end_date}, 原始{len(klines)}条, 过滤后{len(bars)}条")

            # 如果仍然不足 60 条，尝试备用源补齐
            if len(bars) < 60:
                logger.info(f"回测数据不足60条({len(bars)}条)，尝试备用源补齐")
                fallback_bars = await KlineDataFetcher._try_fallback(code, start_date, end_date, count)
                if fallback_bars:
                    # 合并去重（按日期去重）
                    seen_dates = {b.date for b in bars}
                    for fb in fallback_bars:
                        if fb.date not in seen_dates:
                            bars.append(fb)
                            seen_dates.add(fb.date)
                    bars.sort(key=lambda b: b.date)
                    logger.info(f"回测数据备用源补齐后: {len(bars)}条")

            return bars

        except Exception as e:
            logger.error(f"回测数据获取异常: {code}, count={count}, error={e}", exc_info=True)
            return []
