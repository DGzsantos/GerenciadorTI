"""
routes/topology.py
Endpoints para persistir e recuperar o mapa de topologia Drawflow.

GET  /api/topology        → retorna o mapa salvo (ou 404 se vazio)
POST /api/topology        → salva/atualiza o mapa
DELETE /api/topology      → limpa o mapa salvo
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from models.orm_models import User
from models.schemas import TopologyMapSave, TopologyMapResponse, MessageResponse
from services.auth_service import get_current_user
from services.log_service import log_action
from services import topology_service as svc

router = APIRouter(prefix="/topology", tags=["Topologia de Rede"])


@router.get("", response_model=TopologyMapResponse)
async def get_topology(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna o JSON do mapa Drawflow salvo para a empresa.
    Retorna 404 se ainda não houver mapa salvo (frontend trata como canvas vazio).
    """
    topo = await svc.get_topology(db, current_user.company_id)
    if not topo:
        raise HTTPException(status_code=404, detail="Nenhum mapa salvo ainda.")
    return topo


@router.post("", response_model=TopologyMapResponse)
async def save_topology(
    data: TopologyMapSave,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Salva (ou sobrescreve) o mapa Drawflow da empresa.
    O campo `drawflow_data` deve ser o JSON retornado por `editor.export()`.
    """
    topo = await svc.save_topology(db, current_user.company_id, data)
    await log_action(
        db, current_user.company_id, "save", "topology",
        current_user.id, topo.id, "Mapa de topologia salvo"
    )
    return topo


@router.delete("", response_model=MessageResponse)
async def clear_topology(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove o mapa salvo da empresa (limpa o canvas)."""
    from sqlalchemy import delete as sql_delete
    from models.orm_models import TopologyMap

    await db.execute(
        sql_delete(TopologyMap).where(TopologyMap.company_id == current_user.company_id)
    )
    await db.flush()
    await log_action(db, current_user.company_id, "delete", "topology", current_user.id)
    return MessageResponse(message="Mapa de topologia limpo.")
