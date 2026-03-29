"""
routes/projects.py
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from models.orm_models import User
from models.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, MessageResponse
from services.auth_service import get_current_user
from services.log_service import log_action
from services import project_service as svc

router = APIRouter(prefix="/projects", tags=["Projetos"])


@router.get("", response_model=dict)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await svc.get_projects(db, current_user.company_id, skip, limit, search, status)
    return {"items": items, "total": total}


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await svc.get_project_by_id(db, project_id, current_user.company_id)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.create_project(db, data, current_user.company_id)
    await log_action(db, current_user.company_id, "create", "project", current_user.id, obj.id, obj.name)
    return obj


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, data: ProjectUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.update_project(db, project_id, data, current_user.company_id)
    await log_action(db, current_user.company_id, "update", "project", current_user.id, obj.id)
    return obj


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await svc.delete_project(db, project_id, current_user.company_id)
    await log_action(db, current_user.company_id, "delete", "project", current_user.id, project_id)
    return MessageResponse(message="Projeto removido com sucesso.")
