# 🖥️ Gerenciador de TI

Sistema completo de controle interno de TI para empresas. Desenvolvido com **FastAPI + SQLite + Frontend HTML/JS puro**, pronto para evolução SaaS.

---

## 📁 Estrutura do Projeto

```
gerenciador-ti/
├── main.py                    # Entrypoint FastAPI
├── config.py                  # Configurações centralizadas
├── requirements.txt           # Dependências Python
├── vercel.json                # Config de deploy serverless
├── .env.example               # Exemplo de variáveis de ambiente
│
├── database/
│   ├── __init__.py
│   └── connection.py          # Engine SQLAlchemy + sessão assíncrona
│
├── models/
│   ├── __init__.py
│   ├── orm_models.py          # Modelos ORM (tabelas do banco)
│   └── schemas.py             # Schemas Pydantic (validação)
│
├── routes/
│   ├── __init__.py
│   ├── auth.py                # Login, registro, /me
│   ├── equipments.py          # CRUD Equipamentos
│   ├── softwares.py           # CRUD Softwares + alertas
│   ├── infrastructure.py      # CRUD Infraestrutura
│   ├── projects.py            # CRUD Projetos
│   ├── scripts.py             # CRUD Scripts
│   ├── technologies.py        # CRUD Tecnologias
│   └── dashboard.py           # Métricas agregadas
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py        # JWT, hash de senha, auth
│   ├── log_service.py         # Log de atividades
│   ├── equipment_service.py   # Lógica de negócio - equipamentos
│   ├── software_service.py    # Lógica + alertas de vencimento
│   ├── infrastructure_service.py
│   ├── project_service.py
│   ├── script_service.py
│   ├── technology_service.py
│   └── dashboard_service.py   # Agregação de métricas
│
├── frontend/
│   ├── index.html             # SPA completo (HTML + CSS + JS)
│   └── static/
│       └── css/custom.css
│
└── logs/
    └── app.log                # Logs da aplicação
```

---

## 🚀 Como Rodar Localmente

### 1. Pré-requisitos
- Python 3.11+
- pip

### 2. Instalação

```bash
# Clone o projeto
cd gerenciador-ti

# Crie o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
# ou
venv\Scripts\activate           # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env conforme necessário
```

### 3. Rodar

```bash
python main.py
# ou
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Acesse: **http://localhost:8000**

**Login padrão:** `admin` / `admin123`

---

## 📡 API Endpoints

### Autenticação
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/auth/login` | Login — retorna JWT |
| GET | `/api/auth/me` | Dados do usuário atual |
| POST | `/api/auth/register` | Criar usuário (admin) |

### Equipamentos
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/equipments` | Listar (filtros: search, status, type) |
| GET | `/api/equipments/{id}` | Detalhes |
| POST | `/api/equipments` | Criar |
| PUT | `/api/equipments/{id}` | Atualizar |
| DELETE | `/api/equipments/{id}` | Remover |

### Softwares
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/softwares` | Listar (filtros: search, expiring_days) |
| GET | `/api/softwares/alerts` | Softwares próximos do vencimento |
| POST | `/api/softwares/link-equipment` | Associar software a equipamento |

### Infraestrutura
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/infrastructure` | Listar (filtros: search, category) |
| ... | ... | CRUD completo |

### Projetos, Scripts, Tecnologias
Todos com CRUD completo: `GET`, `POST`, `PUT`, `DELETE`

### Dashboard
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/dashboard` | Métricas gerais da empresa |

### Documentação interativa
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

---

## 🗄️ Banco de Dados

### SQLite (padrão)
Arquivo criado automaticamente em `./gerenciador_ti.db`.

### Migrar para PostgreSQL / Supabase

1. Instale o driver async:
   ```bash
   pip install asyncpg
   ```

2. Altere no `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
   ```

3. Execute a aplicação — as tabelas são criadas automaticamente via SQLAlchemy.

---

## 🔐 Segurança

- Senhas com hash **bcrypt**
- Autenticação via **JWT (Bearer Token)**
- Suporte a **roles**: `admin`, `user`, `viewer`
- Multi-tenant via `company_id` em todos os recursos
- Logs de todas as ações sensíveis

**⚠️ Antes de ir para produção:**
```bash
# Gere uma SECRET_KEY forte
openssl rand -hex 32
# Cole no .env: SECRET_KEY=...
```

---

## ☁️ Deploy

### Vercel (Serverless)

```bash
npm i -g vercel
vercel login
vercel

# Configure as variáveis de ambiente no painel Vercel:
# DATABASE_URL, SECRET_KEY
```

> **Nota:** Para produção serverless, recomenda-se usar PostgreSQL (Supabase, Neon, ou outro) ao invés de SQLite.

### Railway / Render (VPS simples)

```bash
# Dockerfile alternativo incluído abaixo
docker build -t gerenciador-ti .
docker run -p 8000:8000 gerenciador-ti
```

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p logs frontend/static/css
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🗺️ Roadmap / Evolução SaaS

- [ ] Plano de assinaturas por empresa (Stripe)
- [ ] Notificações por e-mail (alertas de vencimento)
- [ ] Upload de arquivos (notas fiscais, contratos)
- [ ] Relatórios PDF exportáveis
- [ ] API pública com rate limiting
- [ ] Integração com Active Directory / LDAP
- [ ] App mobile (React Native)
- [ ] Webhooks para integrações externas

---

## 🛠️ Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + Python 3.11 |
| ORM | SQLAlchemy 2.0 (async) |
| Banco | SQLite / PostgreSQL |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Fonts | Syne + JetBrains Mono + Inter |
| Deploy | Vercel / Railway / Docker |
| Logs | Loguru |

---

Desenvolvido como base profissional para sistemas de TI internos.
