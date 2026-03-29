"""
routes/technologies.py
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from models.orm_models import User
from models.schemas import TechnologyCreate, TechnologyUpdate, TechnologyResponse, MessageResponse
from services.auth_service import get_current_user
from services.log_service import log_action
from services import technology_service as svc

router = APIRouter(prefix="/technologies", tags=["Tecnologias"])


@router.get("", response_model=dict)
async def list_technologies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await svc.get_technologies(db, current_user.company_id, skip, limit, search, category)
    return {"items": items, "total": total}


@router.get("/{tech_id}", response_model=TechnologyResponse)
async def get_technology(tech_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await svc.get_technology_by_id(db, tech_id, current_user.company_id)


@router.post("", response_model=TechnologyResponse, status_code=201)
async def create_technology(data: TechnologyCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.create_technology(db, data, current_user.company_id)
    await log_action(db, current_user.company_id, "create", "technology", current_user.id, obj.id, obj.name)
    return obj


@router.put("/{tech_id}", response_model=TechnologyResponse)
async def update_technology(tech_id: int, data: TechnologyUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.update_technology(db, tech_id, data, current_user.company_id)
    await log_action(db, current_user.company_id, "update", "technology", current_user.id, obj.id)
    return obj


@router.delete("/{tech_id}", response_model=MessageResponse)
async def delete_technology(tech_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await svc.delete_technology(db, tech_id, current_user.company_id)
    await log_action(db, current_user.company_id, "delete", "technology", current_user.id, tech_id)
    return MessageResponse(message="Tecnologia removida com sucesso.")
