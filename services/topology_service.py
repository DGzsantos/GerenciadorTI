"""
services/topology_service.py
Lógica para persistir e recuperar o mapa de topologia de rede (Drawflow JSON).
Usa upsert simples: cada empresa tem exatamente um mapa.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.orm_models import TopologyMap
from models.schemas import TopologyMapSave


async def get_topology(db: AsyncSession, company_id: int) -> TopologyMap | None:
    """Retorna o mapa salvo da empresa, ou None se ainda não houver."""
    result = await db.execute(
        select(TopologyMap).where(TopologyMap.company_id == company_id)
    )
    return result.scalar_one_or_none()


async def save_topology(
    db: AsyncSession, company_id: int, data: TopologyMapSave
) -> TopologyMap:
    """
    Upsert: cria o mapa se não existir, atualiza se já houver.
    Retorna o objeto salvo.
    """
    existing = await get_topology(db, company_id)

    if existing:
        existing.name = data.name
        existing.drawflow_data = data.drawflow_data
        await db.flush()
        await db.refresh(existing)
        return existing

    new_map = TopologyMap(
        company_id=company_id,
        name=data.name,
        drawflow_data=data.drawflow_data,
    )
    db.add(new_map)
    await db.flush()
    await db.refresh(new_map)
    return new_map
