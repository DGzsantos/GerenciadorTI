"""
services/software_service.py
Lógica de negócio para Softwares — inclui alertas de vencimento.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Optional, List
from fastapi import HTTPException
from datetime import datetime, timedelta

from models.orm_models import Software, EquipmentSoftware
from models.schemas import SoftwareCreate, SoftwareUpdate, EquipmentSoftwareCreate


def _calc_days_to_expire(sw: Software) -> Optional[int]:
    if sw.valid_until:
        delta = sw.valid_until - datetime.utcnow()
        return delta.days
    return None


async def get_softwares(
    db: AsyncSession,
    company_id: int,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    expiring_days: Optional[int] = None,
) -> tuple[List[Software], int]:
    query = select(Software).where(Software.company_id == company_id)

    if search:
        query = query.where(
            or_(
                Software.name.ilike(f"%{search}%"),
                Software.vendor.ilike(f"%{search}%"),
            )
        )
    if expiring_days is not None:
        threshold = datetime.utcnow() + timedelta(days=expiring_days)
        query = query.where(
            and_(Software.valid_until != None, Software.valid_until <= threshold)
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Software.name))
    items = result.scalars().all()

    # injeta campo calculado
    for sw in items:
        sw.days_to_expire = _calc_days_to_expire(sw)

    return items, total


async def get_software_by_id(db: AsyncSession, software_id: int, company_id: int) -> Software:
    result = await db.execute(
        select(Software).where(Software.id == software_id, Software.company_id == company_id)
    )
    sw = result.scalar_one_or_none()
    if not sw:
        raise HTTPException(status_code=404, detail="Software não encontrado.")
    sw.days_to_expire = _calc_days_to_expire(sw)
    return sw


async def create_software(db: AsyncSession, data: SoftwareCreate, company_id: int) -> Software:
    sw = Software(**data.model_dump(), company_id=company_id)
    db.add(sw)
    await db.flush()
    await db.refresh(sw)
    sw.days_to_expire = _calc_days_to_expire(sw)
    return sw


async def update_software(db: AsyncSession, software_id: int, data: SoftwareUpdate, company_id: int) -> Software:
    sw = await get_software_by_id(db, software_id, company_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sw, field, value)
    await db.flush()
    await db.refresh(sw)
    sw.days_to_expire = _calc_days_to_expire(sw)
    return sw


async def delete_software(db: AsyncSession, software_id: int, company_id: int) -> None:
    sw = await get_software_by_id(db, software_id, company_id)
    await db.delete(sw)
    await db.flush()


async def link_software_to_equipment(
    db: AsyncSession, data: EquipmentSoftwareCreate, company_id: int
) -> EquipmentSoftware:
    link = EquipmentSoftware(**data.model_dump())
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


async def get_expiring_alerts(db: AsyncSession, company_id: int) -> List[Software]:
    """Retorna softwares vencendo dentro do prazo de alerta configurado."""
    result = await db.execute(select(Software).where(Software.company_id == company_id, Software.valid_until != None))
    items = result.scalars().all()
    alerts = []
    for sw in items:
        days = _calc_days_to_expire(sw)
        sw.days_to_expire = days
        if days is not None and days <= sw.alert_days_before:
            alerts.append(sw)
    return alerts
