"""
database/connection.py
Módulo de conexão com o banco de dados SQLite via SQLAlchemy + aiosqlite.
Estruturado para fácil migração para Supabase/PostgreSQL.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    DateTime, Float, ForeignKey, Enum as SAEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from databases import Database
from loguru import logger
from config import settings
import enum

# ──────────────────────────────────────────────
# Engine e sessão assíncronos
# ──────────────────────────────────────────────
DATABASE_URL = settings.DATABASE_URL  # sqlite+aiosqlite:///./gerenciador_ti.db

engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Para migrations síncronas (Alembic)
sync_engine = create_engine(
    DATABASE_URL.replace("sqlite+aiosqlite", "sqlite"),
    connect_args={"check_same_thread": False},
)
SyncSession = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

# Para queries raw (databases lib)
database = Database(DATABASE_URL)


# ──────────────────────────────────────────────
# Dependency para injeção em rotas
# ──────────────────────────────────────────────
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ──────────────────────────────────────────────
# Inicialização do banco (cria tabelas)
# ──────────────────────────────────────────────
async def init_db():
    """Cria todas as tabelas no banco de dados."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Banco de dados inicializado com sucesso.")


async def close_db():
    """Fecha conexões com o banco."""
    await engine.dispose()
    logger.info("🔒 Conexão com banco encerrada.")
