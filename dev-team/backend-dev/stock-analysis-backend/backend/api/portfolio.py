"""
资产组合管理 — API 端点。

遵循设计文档 v1.5。
导航位置：统一导航菜单「资产组合」，位于系统配置之前。
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.portfolio import (
    VirtualAccount, Position, TransactionRecord, Strategy,
    BacktestTask, ClosePositionRecord,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["portfolio"], prefix="/portfolio")


# ─── 依赖：获取当前登录用户 ───

async def _get_current_user(request: Request) -> dict:
    """从请求头解析当前用户"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    token = auth[7:]
    from backend.services.auth_service import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Token无效或已过期")
    try:
        user_id = int(payload.get("sub", 0))
    except (ValueError, TypeError):
        raise HTTPException(401, "用户身份异常")
    if not user_id:
        raise HTTPException(401, "用户身份异常")
    return {"id": user_id, "role": payload.get("role", "user")}


@router.get("/dashboard")
async def dashboard_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """仪表盘资产总览"""
    # 获取用户所有正常账户
    acc_result = await db.execute(
        select(VirtualAccount).where(
            VirtualAccount.status == 1,
            VirtualAccount.user_id == user["id"],
        )
    )
    accounts = acc_result.scalars().all()

    total_initial = 0
    total_cash = 0
    total_position_value = 0
    total_assets = 0
    total_positions = 0
    account_count = len(accounts)

    for acc in accounts:
        total_initial += acc.initial_capital
        total_cash += acc.available_cash
        pos_result = await db.execute(
            select(Position).where(Position.account_id == acc.id)
        )
        positions = pos_result.scalars().all()
        total_positions += len(positions)
        for p in positions:
            val = p.quantity * (p.current_price or p.avg_cost)
            total_position_value += val

    # 清仓记录数
    close_result = await db.execute(
        select(func.count()).select_from(ClosePositionRecord).where(
            ClosePositionRecord.account_id.in_([a.id for a in accounts])
        ) if accounts else select(func.count()).select_from(ClosePositionRecord).where(ClosePositionRecord.id == -1)
    )
    close_count = close_result.scalar() if accounts else 0

    total_assets = total_cash + total_position_value
    total_profit = total_assets - total_initial
    total_profit_rate = (total_profit / total_initial * 100) if total_initial > 0 else 0
    position_ratio = (total_position_value / total_assets * 100) if total_assets > 0 else 0

    return {
        "account_count": account_count,
        "total_initial": round(total_initial, 2),
        "total_cash": round(total_cash, 2),
        "total_position_value": round(total_position_value, 2),
        "total_assets": round(total_assets, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_rate": round(total_profit_rate, 2),
        "position_ratio": round(position_ratio, 2),
        "position_count": total_positions,
        "close_position_count": close_count or 0,
    }


# ─── 辅助函数 ───

def _calc_account_stats(account: VirtualAccount, positions: List[Position]) -> dict:
    """计算账户统计数据：总资产、可用资金、持仓市值、收益率等"""
    position_value = sum(
        (p.quantity * p.current_price) if p.current_price else (p.quantity * p.avg_cost)
        for p in positions
    )
    total_assets = account.available_cash + position_value
    total_profit = total_assets - account.initial_capital
    total_profit_rate = (total_profit / account.initial_capital * 100) if account.initial_capital > 0 else 0
    position_ratio = (position_value / total_assets * 100) if total_assets > 0 else 0

    return {
        "id": account.id,
        "name": account.name,
        "initial_capital": round(account.initial_capital, 2),
        "current_assets": round(total_assets, 2),
        "available_cash": round(account.available_cash, 2),
        "position_value": round(position_value, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_rate": round(total_profit_rate, 2),
        "position_ratio": round(position_ratio, 2),
        "auto_trade_enabled": account.auto_trade_enabled,
        "strategy_id": account.strategy_id,
        "auto_trade_status": account.auto_trade_status,
        "version": account.version,
        "status": account.status,
        "created_at": account.created_at.isoformat() if account.created_at else None,
    }


# ─── 1. 虚拟账户 ───

@router.get("/accounts")
async def list_accounts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """获取当前用户所有虚拟账户列表（含实时统计）"""
    result = await db.execute(
        select(VirtualAccount).where(
            VirtualAccount.status == 1,
            VirtualAccount.user_id == user["id"],
        ).order_by(VirtualAccount.created_at)
    )
    accounts = result.scalars().all()
    items = []
    for acc in accounts:
        pos_result = await db.execute(
            select(Position).where(Position.account_id == acc.id)
        )
        positions = pos_result.scalars().all()
        items.append(_calc_account_stats(acc, positions))
    return {"items": items, "total": len(items)}


@router.post("/accounts")
async def create_account(
    request: Request,
    body: dict = Body(..., example={"name": "短线账户", "initial_capital": 1000000}),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """创建虚拟账户"""
    account = VirtualAccount(
        user_id=user["id"],
        name=body.get("name", "新账户"),
        initial_capital=body.get("initial_capital", 1000000.0),
        available_cash=body.get("initial_capital", 1000000.0),
        current_assets=body.get("initial_capital", 1000000.0),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return {"success": True, "account": _calc_account_stats(account, [])}


@router.put("/accounts/{account_id}")
async def update_account(
    request: Request,
    account_id: int,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """修改账户信息"""
    result = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "账户不存在")
    if account.user_id != user["id"]:
        raise HTTPException(403, "无权修改他人账户")
    if "name" in body:
        account.name = body["name"]
    if "auto_trade_enabled" in body:
        account.auto_trade_enabled = body["auto_trade_enabled"]
    if "strategy_id" in body:
        account.strategy_id = body["strategy_id"]
    if "auto_trade_status" in body:
        account.auto_trade_status = body["auto_trade_status"]
    await db.commit()
    return {"success": True}


@router.post("/accounts/{account_id}/reset")
async def reset_account(
    request: Request,
    account_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """重置账户（清空持仓，恢复初始资金）"""
    result = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "账户不存在")
    if account.user_id != user["id"]:
        raise HTTPException(403, "无权操作他人账户")
    # 清空持仓
    await db.execute(Position.__table__.delete().where(Position.account_id == account_id))
    # 恢复资金
    account.available_cash = account.initial_capital
    account.current_assets = account.initial_capital
    await db.commit()
    return {"success": True, "message": "账户已重置"}


@router.delete("/accounts/{account_id}")
async def archive_account(
    request: Request,
    account_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """归档账户"""
    result = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "账户不存在")
    if account.user_id != user["id"]:
        raise HTTPException(403, "无权操作他人账户")
    account.status = 0
    await db.commit()
    return {"success": True, "message": "账户已归档"}


# ─── 2. 持仓管理 ───

@router.get("/positions/{account_id}")
async def list_positions(
    request: Request,
    account_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """获取指定账户的持仓列表"""
    # 验证账户归属
    acc = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    acc_obj = acc.scalar_one_or_none()
    if not acc_obj:
        raise HTTPException(404, "账户不存在")
    if acc_obj.user_id != user["id"]:
        raise HTTPException(403, "无权查看他人账户")
    result = await db.execute(
        select(Position).where(Position.account_id == account_id).order_by(Position.created_at)
    )
    positions = result.scalars().all()
    items = [{
        "id": p.id,
        "account_id": p.account_id,
        "stock_code": p.stock_code,
        "stock_name": p.stock_name,
        "quantity": p.quantity,
        "avg_cost": round(p.avg_cost, 3),
        "current_price": round(p.current_price, 3) if p.current_price else 0,
        "profit_loss": round(p.profit_loss, 2) if p.profit_loss else 0,
        "profit_loss_rate": round(p.profit_loss_rate, 2) if p.profit_loss_rate else 0,
        "source_type": p.source_type,
        "position_value": round(p.quantity * (p.current_price or p.avg_cost), 2),
        "cost_total": round(p.quantity * p.avg_cost, 2),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    } for p in positions]
    return {"items": items, "total": len(items)}


@router.post("/positions/buy")
async def buy_stock(
    request: Request,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """买入股票"""
    account_id = body.get("account_id")
    stock_code = body.get("stock_code", "")
    stock_name = body.get("stock_name", "")
    quantity = body.get("quantity", 0)
    price = body.get("price", 0.0)
    source_type = body.get("source_type", 0)

    if not account_id or not stock_code or quantity <= 0 or price <= 0:
        raise HTTPException(400, "参数不完整")

    # 检查账户归属
    result = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(404, "账户不存在")
    if account.user_id != user["id"]:
        raise HTTPException(403, "无权操作他人账户")
    if not account:
        raise HTTPException(404, "账户不存在")

    amount = round(quantity * price, 2)
    if account.available_cash < amount:
        raise HTTPException(400, "可用资金不足")

    # 扣除资金
    account.available_cash = round(account.available_cash - amount, 2)

    # 更新或创建持仓
    pos_result = await db.execute(
        select(Position).where(
            Position.account_id == account_id,
            Position.stock_code == stock_code,
        )
    )
    position = pos_result.scalar_one_or_none()
    if position:
        # 加权平均成本
        old_total = position.avg_cost * position.quantity
        new_total = old_total + amount
        new_qty = position.quantity + quantity
        position.avg_cost = round(new_total / new_qty, 3)
        position.quantity = new_qty
    else:
        position = Position(
            account_id=account_id,
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            avg_cost=price,
            current_price=price,
            source_type=source_type,
        )
        db.add(position)

    # 创建交易记录
    record = TransactionRecord(
        account_id=account_id,
        stock_code=stock_code,
        stock_name=stock_name,
        trade_type=1,
        quantity=quantity,
        price=price,
        amount=amount,
        order_status=2,
        strategy_triggered=source_type,
    )
    db.add(record)
    await db.commit()
    return {"success": True, "message": f"买入 {stock_code} {quantity}股 成功"}


@router.post("/positions/sell")
async def sell_stock(
    request: Request,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """卖出股票"""
    account_id = body.get("account_id")
    stock_code = body.get("stock_code", "")
    quantity = body.get("quantity", 0)
    price = body.get("price", 0.0)

    if not account_id or not stock_code or quantity <= 0 or price <= 0:
        raise HTTPException(400, "参数不完整")

    # 验证账户归属
    acc_result = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    acc = acc_result.scalar_one_or_none()
    if not acc:
        raise HTTPException(404, "账户不存在")
    if acc.user_id != user["id"]:
        raise HTTPException(403, "无权操作他人账户")

    result = await db.execute(
        select(Position).where(
            Position.account_id == account_id,
            Position.stock_code == stock_code,
        )
    )
    position = result.scalar_one_or_none()
    if not position or position.quantity < quantity:
        raise HTTPException(400, "持仓不足")

    amount = round(quantity * price, 2)
    is_full_close = (position.quantity == quantity)

    # 更新持仓
    if is_full_close:
        # 清仓：记录到清仓记录表
        hold_days = (datetime.now() - position.created_at).days if position.created_at else 0
        total_profit = round((price - position.avg_cost) * quantity, 2)
        total_profit_rate = round(((price - position.avg_cost) / position.avg_cost) * 100, 2) if position.avg_cost > 0 else 0

        close_record = ClosePositionRecord(
            account_id=account_id,
            stock_code=stock_code,
            stock_name=position.stock_name,
            buy_time=position.created_at,
            sell_time=datetime.now(),
            hold_days=hold_days,
            total_profit=total_profit,
            total_profit_rate=total_profit_rate,
            trade_type=2,
            reason=body.get("reason", "手动清仓"),
        )
        db.add(close_record)
        await db.delete(position)
    else:
        position.quantity -= quantity

    # 回笼资金
    account_result = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    account = account_result.scalar_one_or_none()
    if account:
        account.available_cash = round(account.available_cash + amount, 2)

    # 创建交易记录
    record = TransactionRecord(
        account_id=account_id,
        stock_code=stock_code,
        stock_name=position.stock_name,
        trade_type=2,
        quantity=quantity,
        price=price,
        amount=amount,
        order_status=2,
    )
    db.add(record)
    await db.commit()
    return {"success": True, "message": f"卖出 {stock_code} {quantity}股 成功"}


# ─── 3. 交易记录 ───

@router.get("/transactions/{account_id}")
async def list_transactions(
    request: Request,
    account_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    # 验证账户归属
    acc = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    acc_obj = acc.scalar_one_or_none()
    if not acc_obj:
        raise HTTPException(404, "账户不存在")
    if acc_obj.user_id != user["id"]:
        raise HTTPException(403, "无权查看他人账户")
    """获取交易记录（分页）"""
    offset = (page - 1) * page_size
    result = await db.execute(
        select(TransactionRecord)
        .where(TransactionRecord.account_id == account_id)
        .order_by(desc(TransactionRecord.created_at))
        .offset(offset)
        .limit(page_size)
    )
    records = result.scalars().all()
    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(TransactionRecord).where(
            TransactionRecord.account_id == account_id
        )
    )
    total = count_result.scalar()
    return {
        "items": [{
            "id": r.id,
            "account_id": r.account_id,
            "stock_code": r.stock_code,
            "stock_name": r.stock_name,
            "trade_type": r.trade_type,
            "trade_type_label": "买入" if r.trade_type == 1 else "卖出",
            "quantity": r.quantity,
            "price": round(r.price, 3),
            "amount": round(r.amount, 2),
            "commission": round(r.commission, 2),
            "strategy_triggered": r.strategy_triggered,
            "strategy_label": "自动" if r.strategy_triggered else "手动",
            "order_status": r.order_status,
            "notes": r.notes or "",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in records],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


# ─── 4. 清仓记录 ───

@router.get("/close-records/{account_id}")
async def list_close_records(
    request: Request,
    account_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    # 验证账户归属
    acc = await db.execute(select(VirtualAccount).where(VirtualAccount.id == account_id))
    acc_obj = acc.scalar_one_or_none()
    if not acc_obj:
        raise HTTPException(404, "账户不存在")
    if acc_obj.user_id != user["id"]:
        raise HTTPException(403, "无权查看他人账户")
    """获取清仓记录"""
    result = await db.execute(
        select(ClosePositionRecord)
        .where(ClosePositionRecord.account_id == account_id)
        .order_by(desc(ClosePositionRecord.created_at))
    )
    records = result.scalars().all()
    return {
        "items": [{
            "id": r.id,
            "stock_code": r.stock_code,
            "stock_name": r.stock_name,
            "buy_time": r.buy_time.isoformat() if r.buy_time else "",
            "sell_time": r.sell_time.isoformat() if r.sell_time else "",
            "hold_days": r.hold_days,
            "total_profit": round(r.total_profit, 2),
            "total_profit_rate": round(r.total_profit_rate, 2),
            "trade_type": r.trade_type,
            "trade_type_label": "手动清仓" if r.trade_type == 2 else "策略清仓",
            "reason": r.reason or "",
        } for r in records],
        "total": len(records),
    }


# ─── 多标的回测结果合并 ───

def _merge_backtest_results(
    results: list, errors: list, all_codes: list
) -> dict:
    """合并多个标的的回测结果为一个综合结果"""
    if not results:
        return {"status": "error", "error": "没有成功的结果"}

    # 加权汇总
    total_initial = sum(r.get("summary", {}).get("initial_capital", 0) for r in results)
    total_final = sum(r.get("summary", {}).get("final_assets", 0) for r in results)
    total_return = ((total_final - total_initial) / total_initial * 100) if total_initial > 0 else 0

    # 合并 equity curve（取第一个标的为主曲线，后续补充）
    primary_result = results[0]

    merged = {
        "status": "ok",
        "stock_count": len(results),
        "total_codes": len(all_codes),
        "failed_count": len(errors),
        "summary": {
            "total_return": round(total_return, 2),
            "annual_return": primary_result.get("summary", {}).get("annual_return", 0),
            "max_drawdown": primary_result.get("summary", {}).get("max_drawdown", 0),
            "win_rate": primary_result.get("summary", {}).get("win_rate", 0),
            "total_trades": sum(r.get("summary", {}).get("total_trades", 0) for r in results),
            "total_close_trades": sum(r.get("summary", {}).get("total_close_trades", 0) for r in results),
            "initial_capital": round(total_initial, 2),
            "final_assets": round(total_final, 2),
            "commission_rate": primary_result.get("summary", {}).get("commission_rate", 0.00025),
        },
        "stock_results": [
            {
                "stock_code": r.get("stock_code", ""),
                "summary": r.get("summary", {}),
                "total_return": r.get("summary", {}).get("total_return", 0),
            }
            for r in results
        ],
        "errors": errors,
        "equity_curve": primary_result.get("equity_curve", []),
        "trades": [t for r in results for t in (r.get("trades", []) or [])],
        "monthly_returns": primary_result.get("monthly_returns", []),
        "backtest_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_range": primary_result.get("data_range", ""),
    }

    # 取最优的年化/回撤/胜率
    best_annual = max(
        (r.get("summary", {}).get("annual_return", 0) or 0) for r in results
    )
    worst_drawdown = max(
        (r.get("summary", {}).get("max_drawdown", 0) or 0) for r in results
    )
    best_win_rate = max(
        (r.get("summary", {}).get("win_rate", 0) or 0) for r in results
    )
    merged["summary"]["annual_return"] = round(best_annual, 2)
    merged["summary"]["max_drawdown"] = round(worst_drawdown, 2)
    merged["summary"]["win_rate"] = round(best_win_rate, 1)

    return merged


# ─── 5. 量化策略 ───

@router.get("/strategies")
async def list_strategies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """获取当前用户的策略列表（如无策略，自动创建默认策略）"""
    result = await db.execute(
        select(Strategy).where(
            Strategy.status == 1,
            Strategy.user_id == user["id"],
        ).order_by(desc(Strategy.created_at))
    )
    strategies = result.scalars().all()
    
    # 如果没有策略，自动创建一个默认策略
    if not strategies:
        default_strategy = Strategy(
            user_id=user["id"],
            name="默认趋势策略",
            strategy_type="趋势跟踪",
            period="日",
            config_json={
                "ma_short": 5,
                "ma_long": 20,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30,
                "stop_loss_pct": 8,
                "take_profit_pct": 20,
            },
            description="默认趋势跟踪策略（基于MA5/MA20金叉死叉信号）",
        )
        db.add(default_strategy)
        await db.commit()
        await db.refresh(default_strategy)
        strategies = [default_strategy]
        logger.info(f"为用户 {user['id']} 自动创建默认策略: {default_strategy.id}")
    
    return {
        "items": [{
            "id": s.id,
            "name": s.name,
            "strategy_type": s.strategy_type,
            "period": s.period,
            "description": s.description,
            "config_json": s.config_json,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        } for s in strategies],
        "total": len(strategies),
    }


@router.post("/strategies")
async def create_strategy(
    request: Request,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """创建策略"""
    strategy = Strategy(
        user_id=user["id"],
        name=body.get("name", "新策略"),
        strategy_type=body.get("strategy_type", "波段"),
        period=body.get("period", "日"),
        config_json=body.get("config_json", {}),
        description=body.get("description", ""),
    )
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return {"success": True, "strategy": {"id": strategy.id, "name": strategy.name}}


@router.put("/strategies/{strategy_id}")
async def update_strategy(
    request: Request,
    strategy_id: int,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """更新策略"""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "策略不存在")
    if strategy.user_id != user["id"]:
        raise HTTPException(403, "无权修改他人策略")
    for key in ["name", "strategy_type", "period", "config_json", "description", "status"]:
        if key in body:
            setattr(strategy, key, body[key])
    await db.commit()
    return {"success": True}


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(
    request: Request,
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """删除策略"""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "策略不存在")
    if strategy.user_id != user["id"]:
        raise HTTPException(403, "无权删除他人策略")
    strategy.status = 0
    await db.commit()
    return {"success": True}


@router.post("/strategies/{strategy_id}/export")
async def export_strategy(
    request: Request,
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """导出策略为 JSON"""
    result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(404, "策略不存在")
    if strategy.user_id != user["id"]:
        raise HTTPException(403, "无权导出他人策略")
    return {
        "name": strategy.name,
        "strategy_type": strategy.strategy_type,
        "period": strategy.period,
        "config_json": strategy.config_json,
        "description": strategy.description,
    }


@router.post("/strategies/import")
async def import_strategy(
    request: Request,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """导入策略"""
    strategy = Strategy(
        user_id=user["id"],
        name=body.get("name", "导入策略"),
        strategy_type=body.get("strategy_type", "波段"),
        period=body.get("period", "日"),
        config_json=body.get("config_json", {}),
        description=body.get("description", ""),
    )
    db.add(strategy)
    await db.commit()
    return {"success": True, "message": "策略导入成功"}


# ─── 6. 回测 ───

@router.post("/backtest")
async def run_backtest(
    request: Request,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """创建并执行回测任务（真实引擎）

    body 字段说明：
    - strategy_id: int, 必填
    - start_date: str, 开始日期 YYYY-MM-DD, 必填
    - end_date: str, 结束日期 YYYY-MM-DD, 必填
    - init_capital: float, 初始资金, 默认 1000000
    - stock_code: str, 单只标的代码（与 stock_codes 二选一）
    - stock_codes: str, 逗号分隔的多只标的代码（与 stock_code 二选一）
    """
    strategy_id = body.get("strategy_id")
    start_date_str = body.get("start_date", "")
    end_date_str = body.get("end_date", "")
    init_capital = body.get("init_capital", 1000000.0)

    # 兼容前端 stock_codes（复数，逗号分隔）和后端 stock_code（单数）
    # 优先级：stock_codes > stock_code
    from backend.config.settings import settings as sys_settings
    raw_stock_codes = body.get("stock_codes", "") or body.get("stock_code", "")
    if not raw_stock_codes:
        raw_stock_codes = sys_settings.default_backtest_stock

    if not strategy_id:
        raise HTTPException(400, "请选择策略")

    # 解析日期
    try:
        start_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d") if start_date_str else datetime.now()
        end_date = datetime.strptime(end_date_str[:10], "%Y-%m-%d") if end_date_str else datetime.now()
    except ValueError:
        raise HTTPException(400, "日期格式错误，请使用 YYYY-MM-DD")

    if start_date >= end_date:
        raise HTTPException(400, "开始日期必须早于结束日期")

    # 验证策略归属
    s_result = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    s = s_result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "策略不存在")
    # admin用户可以查看全部策略
    if user["role"] != "admin" and s.user_id != user["id"]:
        raise HTTPException(403, "无权使用他人策略回测")

    config_json = s.config_json or {}

    # 解析多只标的
    stock_code_list = [c.strip() for c in raw_stock_codes.replace("，", ",").split(",") if c.strip()]
    logger.info(f"回测请求：strategy_id={strategy_id}, stocks={stock_code_list}, "
                f"dates={start_date_str}~{end_date_str}, capital={init_capital}")

    # 创建任务记录
    task = BacktestTask(
        user_id=user["id"],
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date,
        init_capital=init_capital,
        status=1,  # 执行中
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    try:
        from backend.services.backtest_engine import KlineDataFetcher, BacktestEngine

        # 如有多个标的，按比例分配资金
        stock_count = len(stock_code_list)
        capital_per_stock = round(init_capital / stock_count, 2)

        all_results = []
        all_errors = []

        for i, code in enumerate(stock_code_list):
            logger.info(f"回测 [{i+1}/{stock_count}] {code}")
            try:
                bars = await KlineDataFetcher.fetch(
                    code,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    count=600,
                )

                if not bars or len(bars) < 60:
                    msg = f"{code}: K线数据不足（{len(bars or [])}条），至少需要60条"
                    logger.warning(msg)
                    all_errors.append({"code": code, "error": msg})
                    continue

                engine = BacktestEngine(
                    strategy_config=config_json,
                    bars=bars,
                    initial_capital=capital_per_stock,
                )
                result = engine.run()
                result["stock_code"] = code
                all_results.append(result)

            except Exception as e:
                err_msg = f"{code}: {str(e)}"
                logger.error(f"回测 {code} 异常: {e}")
                all_errors.append({"code": code, "error": str(e)})

        if not all_results:
            # 全部失败
            raise ValueError(
                f"所有标的回测均失败: {'; '.join(e['error'] for e in all_errors)}"
            )

        # 合并结果
        combined = _merge_backtest_results(all_results, all_errors, stock_code_list)

        # 保存结果
        task.status = 2  # 完成
        task.result_json = combined
        task.completed_at = datetime.now()
        await db.commit()

        response = {
            "success": True,
            "task_id": task.id,
            "status": 2,
            "result": combined,
            "stock_codes": stock_code_list,
        }
        if all_errors:
            response["warnings"] = [e["error"] for e in all_errors]

        logger.info(f"回测完成: task_id={task.id}, stocks={stock_count}, "
                    f"success={len(all_results)}, failed={len(all_errors)}")
        return response

    except Exception as e:
        logger.error(f"回测执行失败: {e}")
        task.status = 3  # 失败
        task.result_json = {"status": "error", "error": str(e)}
        await db.commit()
        return {
            "success": False,
            "task_id": task.id,
            "status": 3,
            "error": str(e),
        }


@router.delete("/backtest/{task_id}")
async def delete_backtest_task(
    request: Request,
    task_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """删除单条回测记录"""
    result = await db.execute(select(BacktestTask).where(BacktestTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "回测记录不存在")
    if task.user_id != user["id"]:
        raise HTTPException(403, "无权删除他人记录")
    await db.delete(task)
    await db.commit()
    return {"success": True, "message": "回测记录已删除"}


@router.post("/backtest/clear")
async def clear_backtest_tasks(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """清空当前用户所有回测记录"""
    result = await db.execute(
        select(BacktestTask).where(BacktestTask.user_id == user["id"])
    )
    tasks = result.scalars().all()
    for t in tasks:
        await db.delete(t)
    await db.commit()
    return {"success": True, "message": f"已清空 {len(tasks)} 条回测记录"}


@router.get("/backtest/tasks")
async def list_backtest_tasks(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """获取当前用户回测任务列表"""
    result = await db.execute(
        select(BacktestTask).where(
            BacktestTask.user_id == user["id"],
        ).order_by(desc(BacktestTask.created_at)).limit(50)
    )
    tasks = result.scalars().all()
    return {
        "items": [{
            "id": t.id,
            "strategy_id": t.strategy_id,
            "start_date": t.start_date.strftime("%Y-%m-%d") if t.start_date else "",
            "end_date": t.end_date.strftime("%Y-%m-%d") if t.end_date else "",
            "init_capital": round(t.init_capital, 2),
            "result_json": t.result_json,
            "status": t.status,
            "status_label": ["待执行", "执行中", "已完成", "失败"][t.status],
            "created_at": t.created_at.isoformat() if t.created_at else "",
        } for t in tasks],
        "total": len(tasks),
    }
