"""
services/infrastructure_service.py
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
from fastapi import HTTPException
from models.orm_models import Infrastructure
from models.schemas import InfrastructureCreate, InfrastructureUpdate


async def get_infrastructures(db, company_id, skip=0, limit=50, search=None, category=None):
    query = select(Infrastructure).where(Infrastructure.company_id == company_id)
    if category:
        query = query.where(Infrastructure.category == category)
    if search:
        query = query.where(or_(
            Infrastructure.name.ilike(f"%{search}%"),
            Infrastructure.hostname.ilike(f"%{search}%"),
            Infrastructure.ip_address.ilike(f"%{search}%"),
            Infrastructure.provider.ilike(f"%{search}%"),
        ))
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Infrastructure.name))
    return result.scalars().all(), total


async def get_infrastructure_by_id(db, infra_id, company_id):
    result = await db.execute(
        select(Infrastructure).where(Infrastructure.id == infra_id, Infrastructure.company_id == company_id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Infraestrutura não encontrada.")
    return obj


async def create_infrastructure(db, data: InfrastructureCreate, company_id):
    obj = Infrastructure(**data.model_dump(), company_id=company_id)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def update_infrastructure(db, infra_id, data: InfrastructureUpdate, company_id):
    obj = await get_infrastructure_by_id(db, infra_id, company_id)
    for f, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, f, v)
    await db.flush()
    await db.refresh(obj)
    return obj


async def delete_infrastructure(db, infra_id, company_id):
    obj = await get_infrastructure_by_id(db, infra_id, company_id)
    await db.delete(obj)
    await db.flush()
