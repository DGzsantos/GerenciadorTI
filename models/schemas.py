"""
models/schemas.py
Schemas Pydantic — validação de entrada/saída da API.
Separados em: Base, Create, Update, Response.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ──────────────────────────────────────────────
# Enums (espelham os do ORM)
# ──────────────────────────────────────────────
class EquipmentStatus(str, Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    MANUTENCAO = "manutencao"
    DESCARTADO = "descartado"


class ProjectStatus(str, Enum):
    PLANEJAMENTO = "planejamento"
    EM_ANDAMENTO = "em_andamento"
    PAUSADO = "pausado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class InfraCategory(str, Enum):
    SERVIDOR = "servidor"
    REDE = "rede"
    STORAGE = "storage"
    CLOUD = "cloud"
    OUTRO = "outro"


# ══════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════
class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    company_id: int
    role: str


class TokenData(BaseModel):
    username: Optional[str] = None
    company_id: Optional[int] = None
    user_id: Optional[int] = None


# ══════════════════════════════════════════════
# COMPANY
# ══════════════════════════════════════════════
class CompanyBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    cnpj: Optional[str] = None
    email: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# USER
# ══════════════════════════════════════════════
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str
    full_name: Optional[str] = None
    role: str = "user"


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    company_id: int


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    company_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# EQUIPMENT
# ══════════════════════════════════════════════
class EquipmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    type: str = Field(..., max_length=100)
    patrimony: Optional[str] = None
    serial_number: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    responsible_user: Optional[str] = None
    location: Optional[str] = None
    status: EquipmentStatus = EquipmentStatus.ATIVO
    purchase_date: Optional[datetime] = None
    warranty_until: Optional[datetime] = None
    notes: Optional[str] = None


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    patrimony: Optional[str] = None
    serial_number: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    responsible_user: Optional[str] = None
    location: Optional[str] = None
    status: Optional[EquipmentStatus] = None
    purchase_date: Optional[datetime] = None
    warranty_until: Optional[datetime] = None
    notes: Optional[str] = None


class EquipmentResponse(EquipmentBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# SOFTWARE
# ══════════════════════════════════════════════
class SoftwareBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    version: Optional[str] = None
    license_key: Optional[str] = None
    license_type: Optional[str] = None
    max_installations: Optional[int] = None
    vendor: Optional[str] = None
    valid_until: Optional[datetime] = None
    alert_days_before: int = 30
    cost_monthly: Optional[float] = None
    notes: Optional[str] = None
    is_active: bool = True


class SoftwareCreate(SoftwareBase):
    pass


class SoftwareUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    license_key: Optional[str] = None
    license_type: Optional[str] = None
    max_installations: Optional[int] = None
    vendor: Optional[str] = None
    valid_until: Optional[datetime] = None
    alert_days_before: Optional[int] = None
    cost_monthly: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SoftwareResponse(SoftwareBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    days_to_expire: Optional[int] = None  # campo calculado

    class Config:
        from_attributes = True


# ──────────────────────────────
# Associação Equipamento ↔ Software
# ──────────────────────────────
class EquipmentSoftwareCreate(BaseModel):
    equipment_id: int
    software_id: int
    installed_at: Optional[datetime] = None
    notes: Optional[str] = None


class EquipmentSoftwareResponse(BaseModel):
    id: int
    equipment_id: int
    software_id: int
    installed_at: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# INFRASTRUCTURE
# ══════════════════════════════════════════════
class InfrastructureBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    category: InfraCategory = InfraCategory.SERVIDOR
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    os: Optional[str] = None
    provider: Optional[str] = None
    location: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_gb: Optional[float] = None
    disk_gb: Optional[float] = None
    monthly_cost: Optional[float] = None
    contract_until: Optional[datetime] = None
    responsible: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None


class InfrastructureCreate(InfrastructureBase):
    pass


class InfrastructureUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[InfraCategory] = None
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    os: Optional[str] = None
    provider: Optional[str] = None
    location: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_gb: Optional[float] = None
    disk_gb: Optional[float] = None
    monthly_cost: Optional[float] = None
    contract_until: Optional[datetime] = None
    responsible: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class InfrastructureResponse(InfrastructureBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# TECHNOLOGY
# ══════════════════════════════════════════════
class TechnologyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., max_length=100)
    version: Optional[str] = None
    description: Optional[str] = None
    docs_url: Optional[str] = None
    is_active: bool = True


class TechnologyCreate(TechnologyBase):
    pass


class TechnologyUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    docs_url: Optional[str] = None
    is_active: Optional[bool] = None


class TechnologyResponse(TechnologyBase):
    id: int
    company_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# PROJECT
# ══════════════════════════════════════════════
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    responsible: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANEJAMENTO
    progress: int = Field(default=0, ge=0, le=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    repository_url: Optional[str] = None
    production_url: Optional[str] = None
    notes: Optional[str] = None


class ProjectCreate(ProjectBase):
    technology_ids: Optional[List[int]] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    responsible: Optional[str] = None
    status: Optional[ProjectStatus] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    repository_url: Optional[str] = None
    production_url: Optional[str] = None
    notes: Optional[str] = None
    technology_ids: Optional[List[int]] = None


class ProjectResponse(ProjectBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    technologies: Optional[List[TechnologyResponse]] = []

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# SCRIPT
# ══════════════════════════════════════════════
class ScriptBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    language: str = Field(..., max_length=100)
    description: Optional[str] = None
    code: str
    used_in: Optional[str] = None
    tags: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    is_active: bool = True


class ScriptCreate(ScriptBase):
    pass


class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    used_in: Optional[str] = None
    tags: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    is_active: Optional[bool] = None


class ScriptResponse(ScriptBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════
class DashboardResponse(BaseModel):
    total_equipments: int
    equipments_active: int
    equipments_maintenance: int
    total_softwares: int
    softwares_expiring_soon: int   # vencendo nos próximos 30 dias
    total_infrastructure: int
    infrastructure_active: int
    total_projects: int
    projects_in_progress: int
    total_scripts: int
    total_technologies: int
    monthly_cost_infra: float
    monthly_cost_software: float


# ══════════════════════════════════════════════
# GENÉRICO
# ══════════════════════════════════════════════
class MessageResponse(BaseModel):
    message: str
    success: bool = True


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    per_page: int
    total_pages: int


# ══════════════════════════════════════════════
# TOPOLOGY MAP
# ══════════════════════════════════════════════
class TopologyMapSave(BaseModel):
    """Payload para salvar o layout do Drawflow."""
    name: Optional[str] = "Topologia Principal"
    drawflow_data: str  # JSON serializado do Drawflow.export()


class TopologyMapResponse(BaseModel):
    id: int
    company_id: int
    name: str
    drawflow_data: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
