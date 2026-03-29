"""
services/script_service.py
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException
from models.orm_models import Script
from models.schemas import ScriptCreate, ScriptUpdate


async def get_scripts(db, company_id, skip=0, limit=50, search=None, language=None):
    query = select(Script).where(Script.company_id == company_id)
    if language:
        query = query.where(Script.language == language)
    if search:
        query = query.where(or_(
            Script.name.ilike(f"%{search}%"),
            Script.description.ilike(f"%{search}%"),
            Script.tags.ilike(f"%{search}%"),
            Script.used_in.ilike(f"%{search}%"),
        ))
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Script.name))
    return result.scalars().all(), total


async def get_script_by_id(db, script_id, company_id):
    result = await db.execute(
        select(Script).where(Script.id == script_id, Script.company_id == company_id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Script não encontrado.")
    return obj


async def create_script(db, data: ScriptCreate, company_id):
    obj = Script(**data.model_dump(), company_id=company_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_script(db, script_id, data: ScriptUpdate, company_id):
    obj = await get_script_by_id(db, script_id, company_id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_script(db, script_id, company_id):
    obj = await get_script_by_id(db, script_id, company_id)
    await db.delete(obj)
    await db.flush()
