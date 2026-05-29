"""
自动交易执行引擎。

遵循设计文档 v1.5 §6 订单与交易执行机制：
- 按设定频率扫描行情、预警、信号
- 仅执行用户已勾选的规则
- 买入：信号 + 条件全部满足 + 未达持仓上限
- 加仓/减仓：满足任一触发条件 → 执行对应比例
- 卖出/清仓：满足任一条件立即执行
- 所有操作自动记录日志
- 可随时暂停/停止自动交易
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select

from backend.config.database import async_session_factory
from backend.models.portfolio import (
    VirtualAccount, Position, Strategy, TransactionRecord,
)
from backend.services.backtest_engine import (
    KlineDataFetcher, Indicators, SignalEvaluator, Bar,
)

logger = logging.getLogger(__name__)

# 同一股票同一方向的信号去重时间窗口（秒）
SIGNAL_DEDUP_SECONDS = 300


async def run_auto_trade():
    """自动交易引擎主入口：扫描所有开启自动交易的账户并执行"""
    logger.info("自动交易引擎开始扫描...")
    try:
        async with async_session_factory() as db:
            # 查询所有开启自动交易且状态为"运行"的账户
            result = await db.execute(
                select(VirtualAccount).where(
                    VirtualAccount.auto_trade_enabled == 1,
                    VirtualAccount.auto_trade_status == 1,  # 运行中
                    VirtualAccount.status == 1,  # 正常
                )
            )
            accounts = result.scalars().all()

            if not accounts:
                logger.debug("自动交易：没有在运行的账户")
                return

            for account in accounts:
                await _process_account(account)
    except Exception as e:
        logger.error(f"自动交易引擎异常: {e}")


async def _process_account(account: VirtualAccount):
    """处理单个虚拟账户的自动交易"""
    try:
        # 获取绑定策略
        if not account.strategy_id:
            logger.debug(f"账户 {account.id} 未绑定策略")
            return

        async with async_session_factory() as db:
            result = await db.execute(
                select(Strategy).where(Strategy.id == account.strategy_id)
            )
            strategy = result.scalar_one_or_none()
            if not strategy or strategy.status != 1:
                return

            config = strategy.config_json or {}

            # 获取当前持仓
            pos_result = await db.execute(
                select(Position).where(Position.account_id == account.id)
            )
            positions = {p.stock_code: p for p in pos_result.scalars().all()}

            # 获取信号来源的股票列表
            signal_codes = await _get_signal_codes(config, db)

            if not signal_codes:
                logger.debug(f"账户 {account.id}: 信号源为空，跳过")
                return

            # 对每个信号源的股票执行策略检查
            for code in signal_codes:
                await _evaluate_and_trade(
                    db, account, config, positions.get(code), code,
                )
    except Exception as e:
        logger.error(f"账户 {account.id} 自动交易处理失败: {e}")


async def _get_signal_codes(config: dict, db) -> List[str]:
    """根据策略配置获取信号来源股票列表"""
    signals = config.get("signal_sources", {})
    codes = []

    # 监控股票池
    if signals.get("monitor"):
        from backend.models.config import MonitorItem
        result = await db.execute(
            select(MonitorItem).where(MonitorItem.is_active == True)
        )
        codes.extend([item.code for item in result.scalars().all()])

    # 自选股列表
    if signals.get("watchlist"):
        from backend.models.config import WatchlistItem
        result = await db.execute(
            select(WatchlistItem).where(WatchlistItem.is_active == True)
        )
        codes.extend([item.code for item in result.scalars().all()])

    # 去重
    return list(dict.fromkeys(codes))


async def _evaluate_and_trade(
    db, account: VirtualAccount, config: dict,
    position: Optional[Position], code: str,
):
    """对单只股票执行策略评估和交易"""
    # 获取K线数据（用于技术指标计算）
    bars = await KlineDataFetcher.fetch(code, "", "", count=200)
    if not bars or len(bars) < 60:
        return

    idx = len(bars) - 1  # 最新交易日
    bar = bars[idx]
    prices = [b.close for b in bars]

    # 计算技术指标
    ma20 = Indicators.sma(prices, 20)
    indicators = {
        "ma5": Indicators.sma(prices, 5),
        "ma10": Indicators.sma(prices, 10),
        "ma20": ma20,
        "ma_direction": Indicators.ma_direction(prices, 5, 10, 20),
    }
    dif, dea, hist = Indicators.macd(prices)
    indicators["macd"] = (dif, dea, hist)
    indicators["rsi"] = Indicators.rsi(prices, 14)
    k, d, j = Indicators.kdj(bars)
    indicators["kdj"] = (k, d, j)

    buy_rules = config.get("buy_rules", {})
    sell_rules = config.get("sell_rules", {})
    stop_cfg = config.get("stop", {})
    risk_ctrl = config.get("risk_control", {})

    # 检查止盈止损（有持仓时）
    if position:
        stop_result = SignalEvaluator.eval_stop(
            stop_cfg, bar.close, position.avg_cost
        )
        if stop_result:
            reason = "自动止盈" if stop_result == "profit" else "自动止损"
            await _execute_sell(db, account, code, position.stock_name,
                                position.quantity, bar.close, reason)
            logger.info(f"账户{account.id} {code}: {reason}")
            return

    # 检查卖出/减仓信号（有持仓时）
    if position and sell_rules.get("enabled", False):
        sell_signal = SignalEvaluator.eval_sell_signal(
            config, bars, idx, indicators,
            position.avg_cost, 0
        )
        if sell_signal:
            # 减仓或清仓
            reduce_cfg = config.get("reduce_position", {})
            if reduce_cfg.get("enabled", False):
                sell_qty = int(position.quantity * reduce_cfg.get("tier1", 20) / 100 / 100) * 100
                if sell_qty < 100:
                    sell_qty = position.quantity  # 全部卖出
            else:
                sell_qty = position.quantity

            await _execute_sell(db, account, code, position.stock_name,
                                sell_qty, bar.close, "自动卖出信号")
            logger.info(f"账户{account.id} {code}: 卖出 {sell_qty}股")
            return

    # 检查买入信号（无持仓时）
    if not position and buy_rules.get("enabled", False):
        buy_signal = SignalEvaluator.eval_buy_signal(
            config, bars, idx, indicators
        )
        if buy_signal:
            await _execute_buy(db, account, code, bar, config)
            logger.info(f"账户{account.id} {code}: 买入信号触发")


async def _execute_buy(
    db, account: VirtualAccount, code: str,
    bar, config: dict,
):
    """执行买入交易"""
    risk = config.get("risk_control", {})
    max_single_pct = risk.get("single_buy_pct", 20) / 100

    price = bar.close
    buy_amount = account.available_cash * max_single_pct
    quantity = int(buy_amount / price / 100) * 100
    if quantity < 100:
        return

    amount = round(quantity * price, 2)
    if amount > account.available_cash:
        quantity = int(account.available_cash / price / 100) * 100
        if quantity < 100:
            return
        amount = round(quantity * price, 2)

    account.available_cash = round(account.available_cash - amount, 2)

    # 创建持仓
    position = Position(
        account_id=account.id, stock_code=code, stock_name="",
        quantity=quantity, avg_cost=price, current_price=price,
        source_type=1,  # 自动
    )
    db.add(position)

    # 记录交易
    record = TransactionRecord(
        account_id=account.id, stock_code=code,
        trade_type=1, quantity=quantity, price=price,
        amount=amount, order_status=2,
        strategy_triggered=1,
    )
    db.add(record)
    await db.commit()

    logger.info(f"自动买入: 账户{account.id} {code} {quantity}股 @{price}")


async def _execute_sell(
    db, account: VirtualAccount, code: str,
    stock_name: str, quantity: int, price: float,
    reason: str,
):
    """执行卖出交易"""
    # 查找持仓
    result = await db.execute(
        select(Position).where(
            Position.account_id == account.id,
            Position.stock_code == code,
        )
    )
    position = result.scalar_one_or_none()
    if not position or position.quantity < quantity:
        return

    amount = round(quantity * price, 2)
    is_full_close = (position.quantity == quantity)

    if is_full_close:
        await db.delete(position)
    else:
        position.quantity -= quantity

    account.available_cash = round(account.available_cash + amount, 2)

    record = TransactionRecord(
        account_id=account.id, stock_code=code,
        stock_name=stock_name,
        trade_type=2, quantity=quantity, price=price,
        amount=amount, order_status=2,
        strategy_triggered=1,
        notes=reason,
    )
    db.add(record)
    await db.commit()
