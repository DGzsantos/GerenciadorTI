"""
services/equipment_service.py
Lógica de negócio para Equipamentos.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
from fastapi import HTTPException, status

from models.orm_models import Equipment
from models.schemas import EquipmentCreate, EquipmentUpdate


async def get_equipments(
    db: AsyncSession,
    company_id: int,
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    type_filter: Optional[str] = None,
) -> tuple[List[Equipment], int]:
    query = select(Equipment).where(Equipment.company_id == company_id)

    if status_filter:
        query = query.where(Equipment.status == status_filter)
    if type_filter:
        query = query.where(Equipment.type == type_filter)
    if search:
        query = query.where(
            or_(
                Equipment.name.ilike(f"%{search}%"),
                Equipment.patrimony.ilike(f"%{search}%"),
                Equipment.responsible_user.ilike(f"%{search}%"),
                Equipment.serial_number.ilike(f"%{search}%"),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar()

    result = await db.execute(query.offset(skip).limit(limit).order_by(Equipment.created_at.desc()))
    return result.scalars().all(), total


async def get_equipment_by_id(db: AsyncSession, equipment_id: int, company_id: int) -> Equipment:
    result = await db.execute(
        select(Equipment).where(Equipment.id == equipment_id, Equipment.company_id == company_id)
    )
    eq = result.scalar_one_or_none()
    if not eq:
        raise HTTPException(status_code=404, detail="Equipamento não encontrado.")
    return eq


async def create_equipment(db: AsyncSession, data: EquipmentCreate, company_id: int) -> Equipment:
    eq = Equipment(**data.model_dump(), company_id=company_id)
    db.add(eq)
    await db.flush()
    await db.refresh(eq)
    return eq


async def update_equipment(
    db: AsyncSession, equipment_id: int, data: EquipmentUpdate, company_id: int
) -> Equipment:
    eq = await get_equipment_by_id(db, equipment_id, company_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(eq, field, value)
    await db.flush()
    await db.refresh(eq)
    return eq


async def delete_equipment(db: AsyncSession, equipment_id: int, company_id: int) -> None:
    eq = await get_equipment_by_id(db, equipment_id, company_id)
    await db.delete(eq)
    await db.flush()
