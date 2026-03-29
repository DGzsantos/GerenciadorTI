"""
main.py
Ponto de entrada da aplicação FastAPI — Gerenciador de TI.
"""

import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import settings
from database.connection import init_db, close_db
from routes import (
    auth_router, equipment_router, software_router,
    infrastructure_router, project_router, script_router,
    technology_router, dashboard_router, topology_router,
)

# ──────────────────────────────────────────────
# Logger
# ──────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logger.remove()
logger.add(sys.stdout, level=settings.LOG_LEVEL, colorize=True,
           format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
logger.add(settings.LOG_FILE, rotation="10 MB", retention="30 days",
           level=settings.LOG_LEVEL, encoding="utf-8")


# ──────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    await _seed_default_data()
    yield
    await close_db()
    logger.info("👋 Aplicação encerrada.")


async def _seed_default_data():
    """Cria empresa e admin padrão se não existirem."""
    from database.connection import async_session
    from sqlalchemy import select
    from models.orm_models import Company, User
    from services.auth_service import hash_password

    async with async_session() as db:
        result = await db.execute(select(Company).where(Company.id == 1))
        company = result.scalar_one_or_none()
        if not company:
            company = Company(name="Minha Empresa TI", cnpj="00.000.000/0001-00")
            db.add(company)
            await db.flush()

            admin = User(
                company_id=company.id,
                username="admin",
                email="admin@empresa.com",
                full_name="Administrador",
                hashed_password=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            await db.commit()
            logger.info("✅ Dados iniciais criados: admin / admin123")
        else:
            await db.commit()


# ──────────────────────────────────────────────
# App
# ──────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de Gerenciamento de TI — controle de equipamentos, softwares, projetos e infraestrutura.",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Exception Handlers
# ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erro não tratado: {exc} | {request.url}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor.", "success": False},
    )


# ──────────────────────────────────────────────
# Rotas da API
# ──────────────────────────────────────────────
API_PREFIX = "/api"

app.include_router(auth_router,           prefix=API_PREFIX)
app.include_router(dashboard_router,      prefix=API_PREFIX)
app.include_router(equipment_router,      prefix=API_PREFIX)
app.include_router(software_router,       prefix=API_PREFIX)
app.include_router(infrastructure_router, prefix=API_PREFIX)
app.include_router(project_router,        prefix=API_PREFIX)
app.include_router(script_router,         prefix=API_PREFIX)
app.include_router(technology_router,     prefix=API_PREFIX)
app.include_router(topology_router,       prefix=API_PREFIX)


# ──────────────────────────────────────────────
# Frontend estático
# ──────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse("frontend/index.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def catch_all(full_path: str):
    """SPA fallback — redireciona tudo para o index.html."""
    index = "frontend/index.html"
    if os.path.exists(index):
        return FileResponse(index)
    return JSONResponse({"detail": "Not found"}, status_code=404)


# ──────────────────────────────────────────────
# Entrypoint local
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
