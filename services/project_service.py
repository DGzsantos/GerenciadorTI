"""
services/project_service.py
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from fastapi import HTTPException
from models.orm_models import Project, Technology, ProjectTechnology
from models.schemas import ProjectCreate, ProjectUpdate


async def get_projects(db, company_id, skip=0, limit=50, search=None, status_filter=None):
    query = (
        select(Project)
        .options(selectinload(Project.technologies).selectinload(ProjectTechnology.technology))
        .where(Project.company_id == company_id)
    )
    if status_filter:
        query = query.where(Project.status == status_filter)
    if search:
        query = query.where(or_(
            Project.name.ilike(f"%{search}%"),
            Project.responsible.ilike(f"%{search}%"),
        ))
    count_q = select(func.count()).select_from(
        select(Project).where(Project.company_id == company_id).subquery()
    )
    total = (await db.execute(count_q)).scalar()
    result = await db.execute(query.offset(skip).limit(limit).order_by(Project.created_at.desc()))
    return result.scalars().all(), total


async def get_project_by_id(db, project_id, company_id):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.technologies).selectinload(ProjectTechnology.technology))
        .where(Project.id == project_id, Project.company_id == company_id)
    )
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return obj


async def create_project(db, data: ProjectCreate, company_id):
    tech_ids = data.technology_ids or []
    proj_data = data.model_dump(exclude={"technology_ids"})
    proj = Project(**proj_data, company_id=company_id)
    db.add(proj)
    await db.flush()

    for tid in tech_ids:
        link = ProjectTechnology(project_id=proj.id, technology_id=tid)
        db.add(link)
    await db.flush()
    await db.refresh(proj)
    return proj


async def update_project(db, project_id, data: ProjectUpdate, company_id):
    proj = await get_project_by_id(db, project_id, company_id)
    tech_ids = data.technology_ids
    update_data = data.model_dump(exclude_unset=True, exclude={"technology_ids"})
    for f, v in update_data.items():
        setattr(proj, f, v)

    if tech_ids is not None:
        # remover links antigos
        existing = await db.execute(
            select(ProjectTechnology).where(ProjectTechnology.project_id == project_id)
        )
        for link in existing.scalars().all():
            await db.delete(link)
        for tid in tech_ids:
            db.add(ProjectTechnology(project_id=project_id, technology_id=tid))

    await db.flush()
    await db.refresh(proj)
    return proj


async def delete_project(db, project_id, company_id):
    proj = await get_project_by_id(db, project_id, company_id)
    await db.delete(proj)
    await db.flush()
