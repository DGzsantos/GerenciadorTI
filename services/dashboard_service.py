"""
services/dashboard_service.py
Agrega métricas para o painel de controle.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from models.orm_models import (
    Equipment, Software, Infrastructure,
    Project, Script, Technology
)
from models.schemas import DashboardResponse


async def get_dashboard_data(db: AsyncSession, company_id: int) -> DashboardResponse:
    cid = company_id

    async def count(Model, *conditions):
        q = select(func.count()).select_from(Model).where(Model.company_id == cid, *conditions)
        return (await db.execute(q)).scalar() or 0

    async def sum_col(Model, col, *conditions):
        q = select(func.sum(col)).where(Model.company_id == cid, *conditions)
        return (await db.execute(q)).scalar() or 0.0

    now = datetime.utcnow()
    thirty_days = now + timedelta(days=30)

    return DashboardResponse(
        total_equipments=await count(Equipment),
        equipments_active=await count(Equipment, Equipment.status == "ativo"),
        equipments_maintenance=await count(Equipment, Equipment.status == "manutencao"),
        total_softwares=await count(Software),
        softwares_expiring_soon=await count(
            Software,
            Software.valid_until != None,
            Software.valid_until <= thirty_days,
            Software.valid_until >= now,
        ),
        total_infrastructure=await count(Infrastructure),
        infrastructure_active=await count(Infrastructure, Infrastructure.is_active == True),
        total_projects=await count(Project),
        projects_in_progress=await count(Project, Project.status == "em_andamento"),
        total_scripts=await count(Script),
        total_technologies=await count(Technology),
        monthly_cost_infra=float(await sum_col(Infrastructure, Infrastructure.monthly_cost)),
        monthly_cost_software=float(await sum_col(Software, Software.cost_monthly)),
    )
