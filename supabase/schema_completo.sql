-- ═══════════════════════════════════════════════════════════
-- Gerenciador de TI — Tabela: infraestrutura
-- Execute este script no SQL Editor do Supabase
-- ═══════════════════════════════════════════════════════════

-- ── 1. Cria a tabela ─────────────────────────────────────────────────────
create table if not exists public.infraestrutura (
  id            bigserial         primary key,
  user_id       uuid              not null references auth.users(id) on delete cascade,

  -- Identificação
  name          text              not null,
  category      text              not null default 'servidor'
                                  check (category in (
                                    'servidor','switch','roteador','firewall','nobreak',
                                    'access_point','storage','cloud','link','camera','outro'
                                  )),

  -- Rede
  ip_address    text,
  hostname      text,

  -- Hardware / SO
  os            text,
  cpu_cores     integer,
  ram_gb        numeric(8,2),
  disk_gb       numeric(10,2),

  -- Fornecedor / contrato
  provider      text,
  location      text,
  monthly_cost  numeric(12,2),
  contract_until timestamptz,
  responsible   text,
  is_active     boolean           not null default true,

  -- Campo JSONB livre: salve configurações extras, tags, etc.
  dados_json    jsonb             default '{}',

  -- Notas livres
  notes         text,

  -- Timestamps
  created_at    timestamptz       not null default now(),
  updated_at    timestamptz       not null default now()
);

-- ── 2. Índices úteis ──────────────────────────────────────────────────────
create index if not exists idx_infraestrutura_user_id  on public.infraestrutura (user_id);
create index if not exists idx_infraestrutura_category on public.infraestrutura (category);
create index if not exists idx_infraestrutura_is_active on public.infraestrutura (is_active);

-- ── 3. Trigger: atualiza updated_at automaticamente ───────────────────────
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists trg_infraestrutura_updated_at on public.infraestrutura;
create trigger trg_infraestrutura_updated_at
  before update on public.infraestrutura
  for each row execute function public.set_updated_at();

-- ── 4. Row Level Security ─────────────────────────────────────────────────
alter table public.infraestrutura enable row level security;

-- Remove política antiga se existir (idempotente)
drop policy if exists "Usuário acessa apenas seus dados" on public.infraestrutura;

create policy "Usuário acessa apenas seus dados"
  on public.infraestrutura
  for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ── 5. Tabela: topologia (mapa Drawflow — 1 linha por usuário) ────────────
create table if not exists public.topologia (
  id            bigserial   primary key,
  user_id       uuid        not null unique references auth.users(id) on delete cascade,
  name          text        not null default 'Topologia Principal',
  drawflow_data text,       -- JSON serializado de Drawflow.export()
  dados_json    jsonb       default '{}',  -- metadados extras (viewport, zoom, etc.)
  updated_at    timestamptz not null default now()
);

create index if not exists idx_topologia_user_id on public.topologia (user_id);

alter table public.topologia enable row level security;

drop policy if exists "Usuário acessa apenas seus dados" on public.topologia;
create policy "Usuário acessa apenas seus dados"
  on public.topologia
  for all
  using  (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop trigger if exists trg_topologia_updated_at on public.topologia;
create trigger trg_topologia_updated_at
  before update on public.topologia
  for each row execute function public.set_updated_at();

-- ── 6. Demais tabelas (caso ainda não existam) ────────────────────────────
create table if not exists public.equipamentos (
  id              bigserial   primary key,
  user_id         uuid        not null references auth.users(id) on delete cascade,
  name            text        not null,
  type            text        not null default 'outro',
  patrimony       text,
  serial_number   text,
  brand           text,
  model           text,
  responsible_user text,
  location        text,
  status          text        not null default 'ativo'
                              check (status in ('ativo','inativo','manutencao','descartado')),
  purchase_date   timestamptz,
  warranty_until  timestamptz,
  notes           text,
  dados_json      jsonb       default '{}',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
alter table public.equipamentos enable row level security;
drop policy if exists "Usuário acessa apenas seus dados" on public.equipamentos;
create policy "Usuário acessa apenas seus dados" on public.equipamentos
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop trigger if exists trg_equipamentos_updated_at on public.equipamentos;
create trigger trg_equipamentos_updated_at before update on public.equipamentos
  for each row execute function public.set_updated_at();

create table if not exists public.softwares (
  id                bigserial   primary key,
  user_id           uuid        not null references auth.users(id) on delete cascade,
  name              text        not null,
  version           text,
  license_key       text,
  license_type      text        default 'assinatura',
  max_installations integer,
  vendor            text,
  valid_until       timestamptz,
  alert_days_before integer     default 30,
  cost_monthly      numeric(12,2),
  notes             text,
  is_active         boolean     not null default true,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
alter table public.softwares enable row level security;
drop policy if exists "Usuário acessa apenas seus dados" on public.softwares;
create policy "Usuário acessa apenas seus dados" on public.softwares
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop trigger if exists trg_softwares_updated_at on public.softwares;
create trigger trg_softwares_updated_at before update on public.softwares
  for each row execute function public.set_updated_at();

create table if not exists public.projetos (
  id              bigserial   primary key,
  user_id         uuid        not null references auth.users(id) on delete cascade,
  name            text        not null,
  description     text,
  responsible     text,
  status          text        not null default 'planejamento'
                              check (status in ('planejamento','em_andamento','pausado','concluido','cancelado')),
  progress        integer     not null default 0 check (progress between 0 and 100),
  start_date      timestamptz,
  end_date        timestamptz,
  repository_url  text,
  production_url  text,
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
alter table public.projetos enable row level security;
drop policy if exists "Usuário acessa apenas seus dados" on public.projetos;
create policy "Usuário acessa apenas seus dados" on public.projetos
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop trigger if exists trg_projetos_updated_at on public.projetos;
create trigger trg_projetos_updated_at before update on public.projetos
  for each row execute function public.set_updated_at();

create table if not exists public.scripts (
  id          bigserial   primary key,
  user_id     uuid        not null references auth.users(id) on delete cascade,
  name        text        not null,
  language    text        not null,
  description text,
  code        text        not null,
  used_in     text,
  tags        text,
  version     text,
  author      text,
  is_active   boolean     not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
alter table public.scripts enable row level security;
drop policy if exists "Usuário acessa apenas seus dados" on public.scripts;
create policy "Usuário acessa apenas seus dados" on public.scripts
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop trigger if exists trg_scripts_updated_at on public.scripts;
create trigger trg_scripts_updated_at before update on public.scripts
  for each row execute function public.set_updated_at();

create table if not exists public.tecnologias (
  id          bigserial   primary key,
  user_id     uuid        not null references auth.users(id) on delete cascade,
  name        text        not null,
  category    text        not null,
  version     text,
  description text,
  docs_url    text,
  is_active   boolean     not null default true,
  created_at  timestamptz not null default now()
);
alter table public.tecnologias enable row level security;
drop policy if exists "Usuário acessa apenas seus dados" on public.tecnologias;
create policy "Usuário acessa apenas seus dados" on public.tecnologias
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ── Confirmação ───────────────────────────────────────────────────────────
select table_name, obj_description(oid) as descricao
from information_schema.tables t
join pg_class c on c.relname = t.table_name
where table_schema = 'public'
  and table_name in ('infraestrutura','topologia','equipamentos','softwares','projetos','scripts','tecnologias')
order by table_name;
