"""
帮助中心 — API 端点。

路由前缀 /help
公开：分类列表、文档列表/详情、搜索
需登录：提交反馈、联系我们、热门/推荐
管理员：CRUD管理
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.help import (
    HelpCategory,
    HelpDocument,
    HelpDocumentHistory,
    HelpFeedback,
    HelpContact,
)
from backend.services.auth_service import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["help"], prefix="/help")


# ─── 依赖：解析当前用户 ───

async def _get_current_user(request: Request) -> dict:
    """从请求头解析JWT获取当前用户"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    token = auth[7:]
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


async def _require_admin(user: dict = Depends(_get_current_user)) -> dict:
    """要求管理员角色"""
    if user["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user


# ─── 公开接口 ───

@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取分类列表（仅已启用）"""
    result = await db.execute(
        select(HelpCategory)
        .where(HelpCategory.status == 1)
        .order_by(HelpCategory.sort_order)
    )
    categories = result.scalars().all()
    return {
        "items": [{
            "id": c.id,
            "name": c.name,
            "icon": c.icon,
            "sort_order": c.sort_order,
        } for c in categories],
        "total": len(categories),
    }


@router.get("/documents")
async def list_documents(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[int] = Query(1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """文档列表（分页，支持按分类/搜索过滤）"""
    query = select(HelpDocument)

    if status is not None:
        query = query.where(HelpDocument.status == status)
    if category_id is not None:
        query = query.where(HelpDocument.category_id == category_id)
    if search:
        like = f"%{search}%"
        query = query.where(
            or_(
                HelpDocument.title.like(like),
                HelpDocument.content.like(like),
                HelpDocument.tags.like(like),
            )
        )

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(HelpDocument.sort_order).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    docs = result.scalars().all()

    return {
        "items": [{
            "id": d.id,
            "category_id": d.category_id,
            "title": d.title,
            "slug": d.slug,
            "summary": d.summary,
            "tags": d.tags.split(",") if d.tags else [],
            "read_time": d.read_time,
            "author": d.author,
            "view_count": d.view_count,
            "like_count": d.like_count,
            "dislike_count": d.dislike_count,
            "sort_order": d.sort_order,
            "status": d.status,
            "version": d.version,
            "published_at": d.published_at.isoformat() if d.published_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        } for d in docs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/documents/{doc_id}")
async def get_document_by_id(doc_id: int, db: AsyncSession = Depends(get_db)):
    """按ID获取文档详情（自动增加浏览量）"""
    result = await db.execute(select(HelpDocument).where(HelpDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")

    # 增加浏览量
    doc.view_count = (doc.view_count or 0) + 1
    await db.commit()

    # 获取分类名
    cat_result = await db.execute(select(HelpCategory).where(HelpCategory.id == doc.category_id))
    cat = cat_result.scalar_one_or_none()

    return {
        "id": doc.id,
        "category_id": doc.category_id,
        "category_name": cat.name if cat else "",
        "title": doc.title,
        "slug": doc.slug,
        "content": doc.content,
        "summary": doc.summary,
        "tags": doc.tags.split(",") if doc.tags else [],
        "read_time": doc.read_time,
        "author": doc.author,
        "view_count": doc.view_count,
        "like_count": doc.like_count,
        "dislike_count": doc.dislike_count,
        "status": doc.status,
        "version": doc.version,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@router.get("/documents/slug/{slug}")
async def get_document_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """按slug获取文档详情（自动增加浏览量）"""
    result = await db.execute(select(HelpDocument).where(HelpDocument.slug == slug))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")

    # 增加浏览量
    doc.view_count = (doc.view_count or 0) + 1
    await db.commit()

    # 获取分类名
    cat_result = await db.execute(select(HelpCategory).where(HelpCategory.id == doc.category_id))
    cat = cat_result.scalar_one_or_none()

    return {
        "id": doc.id,
        "category_id": doc.category_id,
        "category_name": cat.name if cat else "",
        "title": doc.title,
        "slug": doc.slug,
        "content": doc.content,
        "summary": doc.summary,
        "tags": doc.tags.split(",") if doc.tags else [],
        "read_time": doc.read_time,
        "author": doc.author,
        "view_count": doc.view_count,
        "like_count": doc.like_count,
        "dislike_count": doc.dislike_count,
        "status": doc.status,
        "version": doc.version,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@router.get("/search")
async def search_documents(q: str = Query(""), db: AsyncSession = Depends(get_db)):
    """全文搜索（标题+内容+tags）"""
    if not q.strip():
        return {"items": [], "total": 0}

    like = f"%{q.strip()}%"
    query = (
        select(HelpDocument)
        .where(
            HelpDocument.status == 1,
            or_(
                HelpDocument.title.like(like),
                HelpDocument.content.like(like),
                HelpDocument.tags.like(like),
            ),
        )
        .order_by(desc(HelpDocument.view_count))
        .limit(50)
    )
    result = await db.execute(query)
    docs = result.scalars().all()

    return {
        "items": [{
            "id": d.id,
            "category_id": d.category_id,
            "title": d.title,
            "slug": d.slug,
            "summary": d.summary,
            "tags": d.tags.split(",") if d.tags else [],
            "read_time": d.read_time,
            "view_count": d.view_count,
        } for d in docs],
        "total": len(docs),
    }


# ─── 需登录接口 ───

@router.post("/feedback")
async def submit_feedback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """提交文档反馈（有用/无用）"""
    body = await request.json()
    document_id = body.get("document_id")
    feedback_type = body.get("feedback_type", 1)  # 1有用 2无用
    reason = body.get("reason", "")

    if feedback_type not in (1, 2):
        raise HTTPException(400, "feedback_type 只能为1(有用)或2(无用)")

    # 如果有关联文档，更新计数
    if document_id:
        doc_result = await db.execute(select(HelpDocument).where(HelpDocument.id == document_id))
        doc = doc_result.scalar_one_or_none()
        if doc:
            if feedback_type == 1:
                doc.like_count = (doc.like_count or 0) + 1
            else:
                doc.dislike_count = (doc.dislike_count or 0) + 1

    # 记录反馈
    feedback = HelpFeedback(
        document_id=document_id,
        feedback_type=feedback_type,
        reason=reason,
        user_id=user["id"],
        user_agent=request.headers.get("User-Agent", ""),
    )
    db.add(feedback)
    await db.commit()
    return {"success": True, "message": "感谢您的反馈"}


@router.post("/contact")
async def submit_contact(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(_get_current_user),
):
    """提交联系/问题反馈"""
    body = await request.json()
    contact_type = body.get("type", 5)
    title = body.get("title", "")
    content = body.get("content", "")
    contact = body.get("contact", "")

    if not title.strip() or not content.strip():
        raise HTTPException(400, "标题和描述不能为空")

    record = HelpContact(
        type=contact_type,
        title=title,
        content=content,
        contact=contact,
        user_id=user["id"],
    )
    db.add(record)
    await db.commit()
    return {"success": True, "message": "提交成功，我们会尽快处理"}


@router.get("/hot")
async def get_hot_documents(db: AsyncSession = Depends(get_db)):
    """热门文档（按浏览量TOP20）"""
    result = await db.execute(
        select(HelpDocument)
        .where(HelpDocument.status == 1)
        .order_by(desc(HelpDocument.view_count))
        .limit(20)
    )
    docs = result.scalars().all()
    return {
        "items": [{
            "id": d.id,
            "category_id": d.category_id,
            "title": d.title,
            "slug": d.slug,
            "summary": d.summary,
            "view_count": d.view_count,
            "like_count": d.like_count,
        } for d in docs],
        "total": len(docs),
    }


@router.get("/recommend")
async def get_recommend_documents(
    document_id: int = Query(..., description="当前文档ID"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """推荐文档（同分类的其他文档）"""
    # 获取当前文档的分类
    doc_result = await db.execute(select(HelpDocument).where(HelpDocument.id == document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        return {"items": [], "total": 0}

    result = await db.execute(
        select(HelpDocument)
        .where(
            HelpDocument.category_id == doc.category_id,
            HelpDocument.id != document_id,
            HelpDocument.status == 1,
        )
        .order_by(desc(HelpDocument.view_count))
        .limit(limit)
    )
    docs = result.scalars().all()
    return {
        "items": [{
            "id": d.id,
            "title": d.title,
            "slug": d.slug,
            "summary": d.summary,
            "read_time": d.read_time,
        } for d in docs],
        "total": len(docs),
    }


# ─── 管理员接口 ───
# 由于FastAPI依赖注入嵌套需额外注册，这里用单独的prefix

admin_router = APIRouter(tags=["admin-help"], prefix="/admin/help", dependencies=[Depends(_require_admin)])


@admin_router.post("/categories")
async def create_category(request: Request, db: AsyncSession = Depends(get_db)):
    """创建分类"""
    body = await request.json()
    cat = HelpCategory(
        name=body.get("name", ""),
        icon=body.get("icon", ""),
        sort_order=body.get("sort_order", 0),
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return {"success": True, "category": {"id": cat.id, "name": cat.name}}


@admin_router.put("/categories/{category_id}")
async def update_category(category_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """更新分类"""
    result = await db.execute(select(HelpCategory).where(HelpCategory.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "分类不存在")

    body = await request.json()
    for key in ("name", "icon", "sort_order", "status"):
        if key in body:
            setattr(cat, key, body[key])
    await db.commit()
    return {"success": True}


@admin_router.delete("/categories/{category_id}")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """删除分类"""
    result = await db.execute(select(HelpCategory).where(HelpCategory.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(404, "分类不存在")
    await db.delete(cat)
    await db.commit()
    return {"success": True, "message": "分类已删除"}


@admin_router.post("/documents")
async def create_document(request: Request, db: AsyncSession = Depends(get_db)):
    """创建文档"""
    body = await request.json()
    now = datetime.now()
    status_val = body.get("status", 0)
    doc = HelpDocument(
        category_id=body.get("category_id", 1),
        title=body.get("title", ""),
        slug=body.get("slug", ""),
        content=body.get("content", ""),
        summary=body.get("summary", ""),
        tags=body.get("tags", ""),
        read_time=body.get("read_time", 0),
        author=body.get("author", "系统"),
        sort_order=body.get("sort_order", 0),
        status=status_val,
        version=1,
        published_at=now if status_val == 1 else None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return {"success": True, "document": {"id": doc.id, "title": doc.title, "slug": doc.slug}}


@admin_router.put("/documents/{doc_id}")
async def update_document(doc_id: int, request: Request, db: AsyncSession = Depends(get_db), user: dict = Depends(_require_admin)):
    """更新文档（自动创建版本历史）"""
    result = await db.execute(select(HelpDocument).where(HelpDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")

    body = await request.json()

    # 保存旧内容到版本历史
    history = HelpDocumentHistory(
        document_id=doc.id,
        version=doc.version,
        content=doc.content,
        change_log=body.get("change_log", f"更新至 v{doc.version + 1}"),
        operator=user.get("username", "管理员"),
    )
    db.add(history)

    # 更新字段
    updatable = ("category_id", "title", "slug", "content", "summary", "tags", "read_time", "author", "sort_order")
    for key in updatable:
        if key in body:
            setattr(doc, key, body[key])

    doc.version = doc.version + 1 if doc.version else 2

    # 如果状态从草稿变发布
    if body.get("status") == 1 and doc.status != 1:
        doc.published_at = datetime.now()

    if "status" in body:
        doc.status = body["status"]

    await db.commit()
    return {"success": True, "version": doc.version}


@admin_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """删除文档"""
    result = await db.execute(select(HelpDocument).where(HelpDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")
    await db.delete(doc)
    await db.commit()
    return {"success": True, "message": "文档已删除"}


@admin_router.post("/documents/{doc_id}/publish")
async def publish_document(doc_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """发布/下架文档"""
    result = await db.execute(select(HelpDocument).where(HelpDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")

    body = await request.json()
    new_status = body.get("status", 1)
    if new_status not in (1, 2):
        raise HTTPException(400, "status 只能为1(发布)或2(下架)")

    doc.status = new_status
    if new_status == 1:
        doc.published_at = datetime.now()
    await db.commit()
    status_label = "已发布" if new_status == 1 else "已下架"
    return {"success": True, "message": f"文档{status_label}"}


@admin_router.get("/contacts")
async def list_contacts(
    status: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """反馈列表"""
    query = select(HelpContact)
    if status is not None:
        query = query.where(HelpContact.status == status)
    query = query.order_by(desc(HelpContact.created_at))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    type_labels = {1: "使用问题", 2: "Bug", 3: "建议", 4: "文档", 5: "其他"}
    status_labels = {0: "待处理", 1: "处理中", 2: "已解决", 3: "已关闭"}

    return {
        "items": [{
            "id": c.id,
            "type": c.type,
            "type_label": type_labels.get(c.type, "其他"),
            "title": c.title,
            "content": c.content,
            "contact": c.contact,
            "user_id": c.user_id,
            "status": c.status,
            "status_label": status_labels.get(c.status, "待处理"),
            "reply": c.reply or "",
            "replied_by": c.replied_by or "",
            "replied_at": c.replied_at.isoformat() if c.replied_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@admin_router.post("/contacts/{contact_id}/reply")
async def reply_contact(contact_id: int, request: Request, db: AsyncSession = Depends(get_db), user: dict = Depends(_require_admin)):
    """回复反馈"""
    result = await db.execute(select(HelpContact).where(HelpContact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "反馈不存在")

    body = await request.json()
    contact.reply = body.get("reply", "")
    contact.replied_by = user.get("username", "管理员")
    contact.replied_at = datetime.now()
    contact.status = 2  # 已解决
    await db.commit()
    return {"success": True, "message": "回复成功"}


@admin_router.get("/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)):
    """统计信息"""
    # 文档数
    doc_count = (await db.execute(select(func.count()).select_from(HelpDocument))).scalar() or 0
    published_count = (await db.execute(
        select(func.count()).select_from(HelpDocument).where(HelpDocument.status == 1)
    )).scalar() or 0
    draft_count = (await db.execute(
        select(func.count()).select_from(HelpDocument).where(HelpDocument.status == 0)
    )).scalar() or 0

    # 分类数
    cat_count = (await db.execute(select(func.count()).select_from(HelpCategory))).scalar() or 0

    # 反馈数
    feedback_count = (await db.execute(select(func.count()).select_from(HelpFeedback))).scalar() or 0

    # 联系数
    contact_count = (await db.execute(select(func.count()).select_from(HelpContact))).scalar() or 0
    pending_contact = (await db.execute(
        select(func.count()).select_from(HelpContact).where(HelpContact.status == 0)
    )).scalar() or 0

    # 总浏览量
    total_views = (await db.execute(
        select(func.coalesce(func.sum(HelpDocument.view_count), 0))
    )).scalar() or 0

    return {
        "documents": {"total": doc_count, "published": published_count, "draft": draft_count},
        "categories": cat_count,
        "feedbacks": feedback_count,
        "contacts": {"total": contact_count, "pending": pending_contact},
        "total_views": total_views,
    }


async def init_help_data():
    """首次启动时创建默认分类和核心帮助文档"""
    from backend.config.database import async_session_factory
    from backend.models.help import HelpCategory, HelpDocument

    async with async_session_factory() as db:
        existing_docs = await db.execute(select(HelpDocument).limit(1))
        if existing_docs.first():
            return
        # 获取或创建分类
        cat_result = await db.execute(select(HelpCategory).order_by(HelpCategory.sort_order))
        categories = list(cat_result.scalars().all())
        if not categories:
            categories = [
                HelpCategory(name="新手指南", icon="🚀", sort_order=1),
                HelpCategory(name="功能文档", icon="📚", sort_order=2),
                HelpCategory(name="常见问题", icon="❓", sort_order=3),
                HelpCategory(name="策略知识", icon="📊", sort_order=4),
                HelpCategory(name="视频教程", icon="🎬", sort_order=5),
                HelpCategory(name="联系我们", icon="📧", sort_order=6),
            ]
            for cat in categories:
                db.add(cat)
            await db.flush()
            cat_result = await db.execute(select(HelpCategory).order_by(HelpCategory.sort_order))
            categories = list(cat_result.scalars().all())

        now = datetime.now()
        documents = [
            # ── 新手指南（category_id=categories[0].id）──
            HelpDocument(category_id=categories[0].id, title="系统概述与核心概念", slug="system-overview",
                summary="了解系统能做什么以及核心功能介绍",
                content="# 系统概述与核心概念\n\n## 系统能做什么？\n本系统提供从数据采集、智能选股、技术分析到资产管理的完整投资流程。\n\n## 核心功能模块\n- **仪表盘**：系统状态总览，实时监控行情\n- **实时行情**：查看股票实时价格和技术指标\n- **智能选股**：固定规则和自定义选股策略\n- **智能分析**：AI驱动的个股分析和盘后复盘\n- **智能预警**：七维预警体系，实时风险监控\n- **资产组合**：虚拟账户、持仓管理、量化策略、回测\n- **系统配置**：自选股、监控池、数据源管理",
                tags="系统概述,模块介绍", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[0].id, title="首次登录与个人设置", slug="first-login",
                summary="登录系统、修改密码、设置个人偏好",
                content="# 首次登录与个人设置\n\n## 登录系统\n默认账号：admin / admin123\n演示账号：demo / demo123\n\n## 个性化设置\n在系统配置 → 用户偏好中可设置主题（浅色/深色）、刷新频率等。",
                tags="登录,设置,偏好", read_time=3, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[0].id, title="搭建您的监控体系", slug="setup-monitoring",
                summary="如何添加自选股和构建监控股票池",
                content="# 搭建监控体系\n\n## 添加自选股\n在系统配置 → 自选股管理中可添加股票代码。\n\n## 构建监控池\n监控池用于预警引擎持续跟踪。在系统配置 → 监控池管理中添加。\n\n## 区别\n自选股用于快速查看，监控池用于预警触发。",
                tags="自选股,监控池", read_time=4, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[0].id, title="使用智能选股", slug="using-selection",
                summary="固定规则选股和自定义选股的使用方法",
                content="# 使用智能选股\n\n## 固定规则选股\n系统内置3套策略模板：稳健趋势型、反转突破型、短线强势型，一键运行即可获得选股结果。\n\n## 自定义选股\n按四大维度（范围、基本面、技术面、共振）构建专属筛选条件，可保存为模板复用。",
                tags="智能选股,固定规则,自定义", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[0].id, title="理解预警信号", slug="understanding-warnings",
                summary="七维预警体系和颜色语义说明",
                content="# 理解预警信号\n\n## 七维预警体系\n价格预警、涨跌预警、趋势预警、共振预警、财务预警、事件预警、风险评分。\n\n## 颜色语义\n- 🟢 安全 / 🟡 关注 / 🔴 危险 / 🔵 极端 / ⚫ 严重",
                tags="预警,颜色语义", read_time=4, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[0].id, title="创建第一个资产组合", slug="first-portfolio",
                summary="创建虚拟账户、配置策略、开启自动交易",
                content="# 创建第一个资产组合\n\n1. 进入资产组合模块，点击新建账户\n2. 设置初始资金（默认100万）\n3. 手动买入股票或配置量化策略\n4. 开启自动交易让系统按策略执行\n5. 在回测平台验证策略效果",
                tags="资产组合,账户,策略", read_time=6, author="系统管理员", status=1, published_at=now),

            # ── 功能文档（category_id=categories[1].id）──
            HelpDocument(category_id=categories[1].id, title="仪表盘使用详解", slug="dashboard-guide",
                summary="仪表盘各卡片功能说明",
                content="# 仪表盘使用详解\n\n仪表盘包含：A股概况、盘前提示、实时行情监控、ST股票、突发事件、财经新闻、巨潮公告、自选股、资产管理、系统资源等卡片。",
                tags="仪表盘,卡片", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="实时行情模块详解", slug="market-guide",
                summary="实时行情查看与操作指南",
                content="# 实时行情模块\n\n支持查看A股实时行情，可切换不同市场板块。数据源自动降级：通达信→东方财富→新浪。",
                tags="实时行情,数据源", read_time=4, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="智能选股（固定规则）详解", slug="fixed-selection",
                summary="五层过滤机制和三套策略模板说明",
                content="# 固定规则选股\n\n## 五层过滤\nL1底层过滤→L2技术粗筛→L3深度精筛→L4财务事件→L5综合评分。\n\n## 三套模板\n- 稳健趋势型：趋势上涨+多头共振+风险≤40\n- 反转突破型：反转趋势+相对价位<40%\n- 短线强势型：趋势强度≥80+多头共振+量比≥1.5",
                tags="选股,固定规则,过滤", read_time=6, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="智能选股（自定义）详解", slug="custom-selection",
                summary="四大筛选维度详细说明",
                content="# 自定义选股\n\n## 四大维度\n- **范围**：行业、市值、流动性\n- **基本面**：PE、PB、ROE、净利润增速\n- **技术面**：均线、MACD、KDJ、RSI、量比\n- **共振**：多指标共振条件组合",
                tags="选股,自定义,维度", read_time=7, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="七维预警体系详解", slug="warning-system",
                summary="预警引擎的七大检测维度说明",
                content="# 七维预警体系\n\n1. 价格预警：监控价格突破上下限\n2. 涨跌预警：监控单日涨跌幅异常\n3. 趋势预警：均线排列变化\n4. 共振预警：多指标共振异常\n5. 财务预警：财务数据恶化\n6. 事件预警：减持、质押等负面事件\n7. 风险评分：综合风险量化",
                tags="预警,七维,风险", read_time=6, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="资产组合管理概览", slug="portfolio-overview",
                summary="资产组合模块功能总览",
                content="# 资产组合管理\n\n涵盖虚拟账户、持仓管理、量化策略、回测平台四大功能。实现从选股→策略→交易→持仓调整→收益追踪的完整投资闭环。",
                tags="资产组合,概览", read_time=3, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="虚拟账户管理", slug="virtual-account",
                summary="创建、编辑、管理虚拟账户",
                content="# 虚拟账户管理\n\n支持创建多个独立账户（短线/中线/长线），每个账户资产、持仓完全隔离。支持手动/自动交易一键切换。",
                tags="账户,虚拟,管理", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="持仓管理与交易", slug="position-trading",
                summary="手动买入卖出操作说明",
                content="# 持仓管理与交易\n\n支持手动买入/卖出/清仓，自动计算加权平均成本、实时盈亏。交易记录永久留存可复盘。",
                tags="持仓,交易,买卖", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="量化策略配置指南", slug="strategy-guide",
                summary="量化策略的完整配置流程",
                content="# 量化策略配置\n\n## 配置步骤\n1. 设置基础信息（名称、类型、周期）\n2. 选择信号来源\n3. 配置买入/卖出规则\n4. 设置加仓/减仓机制\n5. 配置仓位风控\n6. 设置止盈止损",
                tags="策略,量化,配置", read_time=8, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="回测平台使用指南", slug="backtest-guide",
                summary="如何配置和执行策略回测",
                content="# 回测平台\n\n## 回测流程\n1. 选择策略和标的股票\n2. 设定回测周期和初始资金\n3. 执行回测\n4. 查看绩效报告（累计收益、年化、最大回撤、胜率）\n5. 根据结果优化策略参数",
                tags="回测,策略,绩效", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="解读回测报告", slug="backtest-report",
                summary="回测指标的解读方法",
                content="# 解读回测报告\n\n## 关键指标\n- **累计收益率**：总盈利百分比\n- **年化收益率**：折算到每年的收益率\n- **最大回撤**：从峰值下跌的最大幅度\n- **胜率**：盈利交易占比\n- **盈亏比**：平均盈利/平均亏损\n\n结合收益曲线和交易明细综合分析。",
                tags="回测,报告,指标", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="系统配置全览", slug="config-overview",
                summary="系统配置各功能说明",
                content="# 系统配置\n\n包括：系统设置、自选股管理、监控池管理、数据源管理、模板管理、用户偏好、系统状态。",
                tags="配置,系统", read_time=3, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="自选股与监控池管理", slug="watchlist-monitor",
                summary="自选股和监控池的区别与管理",
                content="# 自选股与监控池\n\n自选股：个人关注的股票列表，用于快速查看行情。\n监控池：预警引擎跟踪的股票列表，触发预警推送。\n两者独立管理，可在系统配置中分别添加/删除。",
                tags="自选股,监控池,管理", read_time=4, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="数据源管理与切换", slug="datasource-guide",
                summary="数据源降级策略和手动切换",
                content="# 数据源管理\n\n## 数据源优先级\n交易时段：东方财富→新浪→通达信\n非交易时段：通达信→东方财富\n\n## 手动切换\n在系统配置→数据源管理中可手动切换当前数据源。",
                tags="数据源,切换,配置", read_time=4, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[1].id, title="用户偏好设置", slug="user-preferences",
                summary="个性化设置说明",
                content="# 用户偏好\n\n可设置：主题（浅色/深色）、字体大小、布局模式、刷新间隔、自动刷新、预警提示音、默认导出格式等。",
                tags="偏好,设置,主题", read_time=3, author="系统管理员", status=1, published_at=now),

            # ── 常见问题（category_id=categories[2].id）──
            HelpDocument(category_id=categories[2].id, title="账号与登录FAQ", slug="faq-login",
                summary="忘记密码、登录失败等常见问题",
                content="# 账号与登录FAQ\n\n**Q: 忘记密码怎么办？**\n联系管理员重置密码。\n\n**Q: 登录失败如何处理？**\n检查用户名密码是否正确，确认后端服务是否正常运行。",
                tags="FAQ,账号,登录", read_time=3, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[2].id, title="选股相关FAQ", slug="faq-selection",
                summary="选股结果为空、筛选条件等常见问题",
                content="# 选股相关FAQ\n\n**Q: 为什么选股结果为空？**\n1. 筛选条件过于严格→放宽条件\n2. 非交易时段→盘中数据更完整\n3. 监控池为空→先添加监控标的",
                tags="FAQ,选股,结果", read_time=3, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[2].id, title="预警相关FAQ", slug="faq-warning",
                summary="预警不触发、颜色含义等常见问题",
                content="# 预警相关FAQ\n\n**Q: 预警不触发怎么办？**\n确认股票已在监控池中，检查预警配置参数是否合理。\n\n**Q: 预警颜色如何理解？**\n🟢安全 🟡关注 🔴危险 🔵极端 ⚫严重",
                tags="FAQ,预警,颜色", read_time=3, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[2].id, title="资产组合FAQ", slug="faq-portfolio",
                summary="虚拟账户、自动交易等常见问题",
                content="# 资产组合FAQ\n\n**Q: 虚拟账户和实盘的关系？**\n虚拟账户使用虚拟资金模拟交易，与实盘完全隔离。\n\n**Q: 自动交易安全吗？**\n自动交易在虚拟账户内执行，不影响真实资金。",
                tags="FAQ,资产组合,自动交易", read_time=4, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[2].id, title="系统配置FAQ", slug="faq-config",
                summary="数据源、监控池等常见问题",
                content="# 系统配置FAQ\n\n**Q: 如何更换数据源？**\n系统配置→数据源管理，点击切换按钮。\n\n**Q: 监控池上限是多少？**\n没有硬性上限，建议不超过100只以保证性能。",
                tags="FAQ,配置,数据源", read_time=3, author="系统管理员", status=1, published_at=now),

            # ── 策略知识（category_id=categories[3].id）──
            HelpDocument(category_id=categories[3].id, title="技术指标详解", slug="tech-indicators",
                summary="MA/MACD/KDJ/RSI等常用技术指标说明",
                content="# 技术指标详解\n\n## MA（移动平均线）\n用于识别趋势方向。5日/10日/20日均线是最常用周期。\n\n## MACD\n由快线(DIF)、慢线(DEA)和柱状图组成。金叉买入信号，死叉卖出信号。\n\n## KDJ\n随机指标，反映价格相对位置。低位金叉买入，高位死叉卖出。\n\n## RSI\n相对强弱指标。RSI>70超买，RSI<30超卖。",
                tags="技术指标,MA,MACD,KDJ,RSI", read_time=8, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[3].id, title="什么是多指标共振？", slug="resonance",
                summary="多指标共振策略的原理和应用",
                content="# 多指标共振\n\n## 原理\n当多个技术指标同时指向同一方向时，信号的可靠性大幅提升。\n\n## 应用\n在策略配置中可设置共振条件，指定同时满足N项指标时才触发交易。",
                tags="共振,策略,指标", read_time=5, author="系统管理员", status=1, published_at=now),
            HelpDocument(category_id=categories[3].id, title="仓位管理原则", slug="position-management",
                summary="仓位控制和风险管理基本原则",
                content="# 仓位管理原则\n\n## 核心原则\n1. 单只股票仓位不超过总资产的30%\n2. 单一行业持仓不超过5只\n3. 总仓位上限95%留有余地\n4. 严格执行止盈止损纪律",
                tags="仓位,风控,管理", read_time=4, author="系统管理员", status=1, published_at=now),
        ]
        for doc in documents:
            db.add(doc)

        await db.commit()
        logging.getLogger(__name__).info(f"帮助中心初始化: {len(categories)} 分类, {len(documents)} 文档")

