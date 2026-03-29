"""
routes/infrastructure.py
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from models.orm_models import User
from models.schemas import InfrastructureCreate, InfrastructureUpdate, InfrastructureResponse, MessageResponse
from services.auth_service import get_current_user
from services.log_service import log_action
from services import infrastructure_service as svc

router = APIRouter(prefix="/infrastructure", tags=["Infraestrutura"])


@router.get("", response_model=dict)
async def list_infra(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await svc.get_infrastructures(db, current_user.company_id, skip, limit, search, category)
    return {"items": items, "total": total}


@router.get("/{infra_id}", response_model=InfrastructureResponse)
async def get_infra(infra_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await svc.get_infrastructure_by_id(db, infra_id, current_user.company_id)


@router.post("", response_model=InfrastructureResponse, status_code=201)
async def create_infra(data: InfrastructureCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.create_infrastructure(db, data, current_user.company_id)
    await log_action(db, current_user.company_id, "create", "infrastructure", current_user.id, obj.id, obj.name)
    return obj


@router.put("/{infra_id}", response_model=InfrastructureResponse)
async def update_infra(infra_id: int, data: InfrastructureUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.update_infrastructure(db, infra_id, data, current_user.company_id)
    await log_action(db, current_user.company_id, "update", "infrastructure", current_user.id, obj.id)
    return obj


@router.delete("/{infra_id}", response_model=MessageResponse)
async def delete_infra(infra_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await svc.delete_infrastructure(db, infra_id, current_user.company_id)
    await log_action(db, current_user.company_id, "delete", "infrastructure", current_user.id, infra_id)
    return MessageResponse(message="Infraestrutura removida com sucesso.")
