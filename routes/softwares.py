"""
routes/softwares.py
CRUD para Softwares + alertas de vencimento + associação com equipamentos.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from database.connection import get_db
from models.orm_models import User
from models.schemas import (
    SoftwareCreate, SoftwareUpdate, SoftwareResponse,
    EquipmentSoftwareCreate, EquipmentSoftwareResponse, MessageResponse
)
from services.auth_service import get_current_user
from services.log_service import log_action
from services import software_service as svc

router = APIRouter(prefix="/softwares", tags=["Softwares"])


@router.get("", response_model=dict)
async def list_softwares(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    expiring_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await svc.get_softwares(
        db, current_user.company_id, skip, limit, search, expiring_days
    )
    return {"items": items, "total": total}


@router.get("/alerts", response_model=List[SoftwareResponse])
async def expiry_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna softwares dentro do período de alerta de vencimento."""
    return await svc.get_expiring_alerts(db, current_user.company_id)


@router.get("/{software_id}", response_model=SoftwareResponse)
async def get_software(
    software_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_software_by_id(db, software_id, current_user.company_id)


@router.post("", response_model=SoftwareResponse, status_code=201)
async def create_software(
    data: SoftwareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sw = await svc.create_software(db, data, current_user.company_id)
    await log_action(db, current_user.company_id, "create", "software", current_user.id, sw.id, sw.name)
    return sw


@router.put("/{software_id}", response_model=SoftwareResponse)
async def update_software(
    software_id: int,
    data: SoftwareUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sw = await svc.update_software(db, software_id, data, current_user.company_id)
    await log_action(db, current_user.company_id, "update", "software", current_user.id, sw.id)
    return sw


@router.delete("/{software_id}", response_model=MessageResponse)
async def delete_software(
    software_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await svc.delete_software(db, software_id, current_user.company_id)
    await log_action(db, current_user.company_id, "delete", "software", current_user.id, software_id)
    return MessageResponse(message="Software removido com sucesso.")


@router.post("/link-equipment", response_model=EquipmentSoftwareResponse, status_code=201)
async def link_to_equipment(
    data: EquipmentSoftwareCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Associa um software a um equipamento."""
    link = await svc.link_software_to_equipment(db, data, current_user.company_id)
    await log_action(
        db, current_user.company_id, "link", "equipment_software",
        current_user.id, detail=f"equip={data.equipment_id} sw={data.software_id}"
    )
    return link
