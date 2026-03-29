"""
config.py
Configurações centralizadas da aplicação via variáveis de ambiente.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── Aplicação ──────────────────────────────
    APP_NAME: str = "Gerenciador de TI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Banco de Dados ─────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./gerenciador_ti.db"

    # ── Autenticação JWT ───────────────────────
    SECRET_KEY: str = "TROQUE-ESTA-CHAVE-EM-PRODUCAO-USE-OPENSSL-RAND-HEX-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 horas

    # ── CORS ───────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Logs ───────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
