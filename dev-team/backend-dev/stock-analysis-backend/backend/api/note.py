"""
操盘笔记 API — CRUD 完整实现。

提供笔记的增删改查、置顶、标签筛选功能。
所有笔记按更新时间倒序排列。
"""

import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.database import get_db
from backend.models.note import TradingNote
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["notes"], prefix="/notes")


# ─── Pydantic 模型 ───

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128, description="笔记标题")
    content: str = Field(default="", description="笔记正文")
    stock_code: str = Field(default="", max_length=10, description="关联股票代码")
    stock_name: str = Field(default="", max_length=32, description="关联股票名称")
    tags: str = Field(default="", max_length=256, description="标签，逗号分隔")


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=128)
    content: Optional[str] = None
    stock_code: Optional[str] = Field(None, max_length=10)
    stock_name: Optional[str] = Field(None, max_length=32)
    tags: Optional[str] = Field(None, max_length=256)
    is_pinned: Optional[bool] = None


class NoteOut(BaseModel):
    id: int
    title: str
    content: str
    stock_code: str
    stock_name: str
    tags: str
    is_pinned: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class NoteListOut(BaseModel):
    notes: List[NoteOut]
    total: int


def _fmt_dt(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


async def _note_to_out(note: TradingNote) -> NoteOut:
    return NoteOut(
        id=note.id,
        title=note.title,
        content=note.content,
        stock_code=note.stock_code or "",
        stock_name=note.stock_name or "",
        tags=note.tags or "",
        is_pinned=note.is_pinned or False,
        created_at=_fmt_dt(note.created_at),
        updated_at=_fmt_dt(note.updated_at),
    )


# ─── API 端点 ───

@router.get("", response_model=NoteListOut)
async def list_notes(
    tag: Optional[str] = Query(None, description="按标签筛选"),
    stock: Optional[str] = Query(None, description="按股票代码筛选"),
    keyword: Optional[str] = Query(None, description="标题/内容关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: AsyncSession = Depends(get_db),
):
    """获取笔记列表，支持标签/股票/关键词筛选，分页返回。"""
    # 构建条件列表
    conditions = []
    if tag:
        conditions.append(TradingNote.tags.contains(tag))
    if stock:
        conditions.append(TradingNote.stock_code == stock)
    if keyword:
        kw = f"%{keyword}%"
        conditions.append(
            (TradingNote.title.ilike(kw)) | (TradingNote.content.ilike(kw))
        )

    # 计数（独立查询，不含排序和分页）
    count_query = select(func.count(TradingNote.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total = (await db.execute(count_query)).scalar() or 0

    # 数据查询：排序 + 分页
    query = select(TradingNote)
    if conditions:
        query = query.where(*conditions)
    query = query.order_by(TradingNote.is_pinned.desc(), TradingNote.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    notes = result.scalars().all()

    return NoteListOut(
        notes=[await _note_to_out(n) for n in notes],
        total=total,
    )


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(note_id: int, db: AsyncSession = Depends(get_db)):
    """获取单条笔记详情。"""
    result = await db.execute(select(TradingNote).where(TradingNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return await _note_to_out(note)


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(data: NoteCreate, db: AsyncSession = Depends(get_db)):
    """新建操盘笔记。"""
    note = TradingNote(
        user_id=1,
        title=data.title.strip(),
        content=data.content.strip(),
        stock_code=data.stock_code.strip(),
        stock_name=data.stock_name.strip(),
        tags=data.tags.strip(),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    logger.info(f"新建笔记: id={note.id}, title={note.title}")
    return await _note_to_out(note)


@router.put("/{note_id}", response_model=NoteOut)
async def update_note(note_id: int, data: NoteUpdate, db: AsyncSession = Depends(get_db)):
    """更新操盘笔记。"""
    result = await db.execute(select(TradingNote).where(TradingNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if isinstance(value, str):
                setattr(note, field, value.strip())
            else:
                setattr(note, field, value)

    note.updated_at = datetime.now()
    await db.commit()
    await db.refresh(note)
    logger.info(f"更新笔记: id={note.id}, title={note.title}")
    return await _note_to_out(note)


@router.delete("/{note_id}")
async def delete_note(note_id: int, db: AsyncSession = Depends(get_db)):
    """删除操盘笔记。"""
    result = await db.execute(select(TradingNote).where(TradingNote.id == note_id))
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    await db.delete(note)
    await db.commit()
    logger.info(f"删除笔记: id={note.id}, title={note.title}")
    return {"message": "笔记已删除", "id": note_id}
