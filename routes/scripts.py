"""
routes/scripts.py
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from models.orm_models import User
from models.schemas import ScriptCreate, ScriptUpdate, ScriptResponse, MessageResponse
from services.auth_service import get_current_user
from services.log_service import log_action
from services import script_service as svc

router = APIRouter(prefix="/scripts", tags=["Scripts"])


@router.get("", response_model=dict)
async def list_scripts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    language: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await svc.get_scripts(db, current_user.company_id, skip, limit, search, language)
    return {"items": items, "total": total}


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await svc.get_script_by_id(db, script_id, current_user.company_id)


@router.post("", response_model=ScriptResponse, status_code=201)
async def create_script(data: ScriptCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.create_script(db, data, current_user.company_id)
    await log_action(db, current_user.company_id, "create", "script", current_user.id, obj.id, obj.name)
    return obj


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(script_id: int, data: ScriptUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    obj = await svc.update_script(db, script_id, data, current_user.company_id)
    await log_action(db, current_user.company_id, "update", "script", current_user.id, obj.id)
    return obj


@router.delete("/{script_id}", response_model=MessageResponse)
async def delete_script(script_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await svc.delete_script(db, script_id, current_user.company_id)
    await log_action(db, current_user.company_id, "delete", "script", current_user.id, script_id)
    return MessageResponse(message="Script removido com sucesso.")
