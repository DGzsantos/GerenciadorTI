"""
models/orm_models.py
Modelos ORM SQLAlchemy — mapeamento das tabelas do banco de dados.
Todos os modelos suportam multi-tenant via campo company_id.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, Float, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
import enum


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────
class EquipmentStatus(str, enum.Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    MANUTENCAO = "manutencao"
    DESCARTADO = "descartado"


class ProjectStatus(str, enum.Enum):
    PLANEJAMENTO = "planejamento"
    EM_ANDAMENTO = "em_andamento"
    PAUSADO = "pausado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class InfraCategory(str, enum.Enum):
    SERVIDOR = "servidor"
    REDE = "rede"
    STORAGE = "storage"
    CLOUD = "cloud"
    OUTRO = "outro"


# ──────────────────────────────────────────────
# Empresa (Multi-tenant)
# ──────────────────────────────────────────────
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    cnpj = Column(String(20), unique=True, nullable=True)
    email = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="company")
    equipments = relationship("Equipment", back_populates="company")
    softwares = relationship("Software", back_populates="company")
    infrastructures = relationship("Infrastructure", back_populates="company")
    projects = relationship("Project", back_populates="company")
    scripts = relationship("Script", back_populates="company")
    technologies = relationship("Technology", back_populates="company")
    topology_map = relationship("TopologyMap", uselist=False)


# ──────────────────────────────────────────────
# Usuário
# ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(300), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(50), default="user")  # admin | user | viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="users")


# ──────────────────────────────────────────────
# Log de Atividades
# ──────────────────────────────────────────────
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)   # create | update | delete | login
    resource = Column(String(100), nullable=False)  # equipment | software | ...
    resource_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ──────────────────────────────────────────────
# Equipamentos
# ──────────────────────────────────────────────
class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    type = Column(String(100), nullable=False)       # notebook | desktop | impressora | etc.
    patrimony = Column(String(100), nullable=True, unique=False)  # número de patrimônio
    serial_number = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    model = Column(String(150), nullable=True)
    responsible_user = Column(String(200), nullable=True)
    location = Column(String(200), nullable=True)
    status = Column(SAEnum(EquipmentStatus), default=EquipmentStatus.ATIVO)
    purchase_date = Column(DateTime, nullable=True)
    warranty_until = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="equipments")
    softwares = relationship("EquipmentSoftware", back_populates="equipment")


# ──────────────────────────────────────────────
# Softwares
# ──────────────────────────────────────────────
class Software(Base):
    __tablename__ = "softwares"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    version = Column(String(50), nullable=True)
    license_key = Column(String(300), nullable=True)
    license_type = Column(String(100), nullable=True)   # perpetua | assinatura | freeware
    max_installations = Column(Integer, nullable=True)
    vendor = Column(String(200), nullable=True)
    valid_until = Column(DateTime, nullable=True)
    alert_days_before = Column(Integer, default=30)    # alertar N dias antes do vencimento
    cost_monthly = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="softwares")
    equipment_links = relationship("EquipmentSoftware", back_populates="software")


# ──────────────────────────────────────────────
# Associação Equipamento ↔ Software
# ──────────────────────────────────────────────
class EquipmentSoftware(Base):
    __tablename__ = "equipment_softwares"

    id = Column(Integer, primary_key=True, index=True)
    equipment_id = Column(Integer, ForeignKey("equipments.id"), nullable=False)
    software_id = Column(Integer, ForeignKey("softwares.id"), nullable=False)
    installed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    equipment = relationship("Equipment", back_populates="softwares")
    software = relationship("Software", back_populates="equipment_links")


# ──────────────────────────────────────────────
# Infraestrutura
# ──────────────────────────────────────────────
class Infrastructure(Base):
    __tablename__ = "infrastructures"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(SAEnum(InfraCategory), default=InfraCategory.SERVIDOR)
    ip_address = Column(String(50), nullable=True)
    hostname = Column(String(200), nullable=True)
    os = Column(String(100), nullable=True)
    provider = Column(String(200), nullable=True)    # AWS | Azure | DigitalOcean | local | etc.
    location = Column(String(200), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_gb = Column(Float, nullable=True)
    disk_gb = Column(Float, nullable=True)
    monthly_cost = Column(Float, nullable=True)
    contract_until = Column(DateTime, nullable=True)
    responsible = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="infrastructures")


# ──────────────────────────────────────────────
# Tecnologias
# ──────────────────────────────────────────────
class Technology(Base):
    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)  # backend | frontend | banco | devops | mobile
    version = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    docs_url = Column(String(300), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="technologies")
    project_links = relationship("ProjectTechnology", back_populates="technology")


# ──────────────────────────────────────────────
# Projetos
# ──────────────────────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    responsible = Column(String(200), nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.PLANEJAMENTO)
    progress = Column(Integer, default=0)   # 0-100
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    repository_url = Column(String(300), nullable=True)
    production_url = Column(String(300), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="projects")
    technologies = relationship("ProjectTechnology", back_populates="project")


# ──────────────────────────────────────────────
# Associação Projeto ↔ Tecnologia
# ──────────────────────────────────────────────
class ProjectTechnology(Base):
    __tablename__ = "project_technologies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    technology_id = Column(Integer, ForeignKey("technologies.id"), nullable=False)
    role = Column(String(100), nullable=True)  # ex: "API principal", "ORM"

    project = relationship("Project", back_populates="technologies")
    technology = relationship("Technology", back_populates="project_links")


# ──────────────────────────────────────────────
# Scripts / Códigos
# ──────────────────────────────────────────────
class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(200), nullable=False)
    language = Column(String(100), nullable=False)  # python | bash | sql | js | ...
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=False)
    used_in = Column(String(300), nullable=True)    # onde é utilizado (servidor, projeto, etc.)
    tags = Column(String(300), nullable=True)        # csv: backup, deploy, monitoramento
    version = Column(String(50), nullable=True)
    author = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company", back_populates="scripts")


# ──────────────────────────────────────────────
# Mapa de Topologia de Rede
# ──────────────────────────────────────────────
class TopologyMap(Base):
    __tablename__ = "topology_maps"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True)
    name = Column(String(200), default="Topologia Principal")
    # JSON completo exportado pelo Drawflow (nós, conexões, posições)
    drawflow_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    company = relationship("Company")
