"""
routes/auth.py
Rotas de autenticação e gestão de usuários.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from database.connection import get_db
from models.orm_models import User, Company
from models.schemas import (
    LoginRequest, Token, UserCreate, UserResponse,
    UserUpdate, CompanyCreate, CompanyResponse, MessageResponse
)
from services.auth_service import (
    authenticate_user, create_access_token, hash_password,
    get_current_user, require_role
)
from services.log_service import log_action
from config import settings

router = APIRouter(prefix="/auth", tags=["Autenticação"])


# ─── POST /auth/login ────────────────────────
@router.post("/login", response_model=Token)
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Autentica o usuário e retorna um token JWT."""
    user = await authenticate_user(db, data.username, data.password)
    if not user:
        await log_action(
            db, company_id=0, action="login_failed", resource="auth",
            detail=f"Tentativa falha: {data.username}",
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos."
        )

    token = create_access_token(
        data={"sub": user.username, "company_id": user.company_id, "user_id": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    await log_action(
        db, company_id=user.company_id, action="login", resource="auth",
        user_id=user.id, ip_address=request.client.host if request.client else None
    )
    return Token(
        access_token=token,
        user_id=user.id,
        username=user.username,
        company_id=user.company_id,
        role=user.role,
    )


# ─── POST /auth/register-company ────────────
@router.post("/register-company", response_model=dict, status_code=201)
async def register_company(data: CompanyCreate, db: AsyncSession = Depends(get_db)):
    """Registra nova empresa (tenant) e um admin inicial."""
    company = Company(**data.model_dump())
    db.add(company)
    await db.flush()
    return {"message": "Empresa criada.", "company_id": company.id}


# ─── POST /auth/register ─────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """Cria um novo usuário (apenas admins)."""
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username já existe.")

    user = User(
        **{k: v for k, v in data.model_dump().items() if k != "password"},
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await log_action(db, current_user.company_id, "create", "user", current_user.id, user.id)
    return user


# ─── GET /auth/me ─────────────────────────────
@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


# ─── PUT /auth/me ─────────────────────────────
@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "role":
            continue  # usuário não muda o próprio role
        setattr(current_user, field, value)
    await db.flush()
    await db.refresh(current_user)
    return current_user
