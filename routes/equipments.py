"""
routes/equipments.py
CRUD completo para Equipamentos.
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from models.orm_models import User
from models.schemas import (
    EquipmentCreate, EquipmentUpdate, EquipmentResponse, MessageResponse
)
from services.auth_service import get_current_user
from services.log_service import log_action
from services import equipment_service as svc

router = APIRouter(prefix="/equipments", tags=["Equipamentos"])


@router.get("", response_model=dict)
async def list_equipments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await svc.get_equipments(
        db, current_user.company_id, skip, limit, status, search, type
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_equipment_by_id(db, equipment_id, current_user.company_id)


@router.post("", response_model=EquipmentResponse, status_code=201)
async def create_equipment(
    data: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    eq = await svc.create_equipment(db, data, current_user.company_id)
    await log_action(db, current_user.company_id, "create", "equipment", current_user.id, eq.id, eq.name)
    return eq


@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    eq = await svc.update_equipment(db, equipment_id, data, current_user.company_id)
    await log_action(db, current_user.company_id, "update", "equipment", current_user.id, eq.id)
    return eq


@router.delete("/{equipment_id}", response_model=MessageResponse)
async def delete_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await svc.delete_equipment(db, equipment_id, current_user.company_id)
    await log_action(db, current_user.company_id, "delete", "equipment", current_user.id, equipment_id)
    return MessageResponse(message="Equipamento removido com sucesso.")
