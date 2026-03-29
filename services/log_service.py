"""
services/log_service.py
Serviço de log de atividades: grava ações no banco e no arquivo de log.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from models.orm_models import ActivityLog


async def log_action(
    db: AsyncSession,
    company_id: int,
    action: str,
    resource: str,
    user_id: int = None,
    resource_id: int = None,
    detail: str = None,
    ip_address: str = None,
):
    """Registra uma ação no banco e no arquivo de log."""
    entry = ActivityLog(
        company_id=company_id,
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()

    logger.info(
        f"[LOG] company={company_id} | user={user_id} | {action.upper()} {resource}"
        + (f" #{resource_id}" if resource_id else "")
        + (f" | {detail}" if detail else "")
    )
