"""
routes/dashboard.py
Endpoint de métricas agregadas para o painel.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.orm_models import User
from models.schemas import DashboardResponse
from services.auth_service import get_current_user
from services.dashboard_service import get_dashboard_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna contadores e métricas gerais da empresa."""
    return await get_dashboard_data(db, current_user.company_id)
