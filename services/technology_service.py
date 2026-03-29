"""
services/technology_service.py
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from fastapi import HTTPException
from models.orm_models import Technology
from models.schemas import TechnologyCreate, TechnologyUpdate


async def get_technologies(db, company_id, skip=0, limit=100, search=None, category=None):
    query = select(Technology).where(Technology.company_id == company_id)
    if category:
        query = query.where(Technology.category == category)
    if search:
        query = query.where(or_(
            Technology.name.ilike(f"%{search}%"),
            Technology.description.ilike(f"%{search}%"),
        ))
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Technology.name))
    return result.scalars().all(), total


async def get_technology_by_id(db, tech_id, company_id):
    result = await db.execute(
        select(Technology).where(Technology.id == tech_id, Technology.company_id == company_id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Tecnologia não encontrada.")
    return obj


async def create_technology(db, data: TechnologyCreate, company_id):
    obj = Technology(**data.model_dump(), company_id=company_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_technology(db, tech_id, data: TechnologyUpdate, company_id):
    obj = await get_technology_by_id(db, tech_id, company_id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_technology(db, tech_id, company_id):
    obj = await get_technology_by_id(db, tech_id, company_id)
    await db.delete(obj)
    await db.flush()
