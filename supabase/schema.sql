-- ═══════════════════════════════════════════════════════════
-- Gerenciador de TI — Schema Supabase COMPLETO
-- Execute TODO este bloco no SQL Editor do Supabase
-- É idempotente: pode ser re-executado sem erros
-- ═══════════════════════════════════════════════════════════

-- ──────────────────────────────────────────────
-- TABELA: profiles  (vinculada ao auth.users)
-- Criada automaticamente para cada novo usuário
-- via trigger. Contém full_name e role.
-- ──────────────────────────────────────────────
create table if not exists public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  full_name   text,
  email       text,
  role        text not null default 'user'
              check (role in ('user','elevated','admin')),
  avatar_url  text,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- Trigger: cria perfil automaticamente ao registrar usuário
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, email, full_name, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email,'@',1)),
    coalesce(new.raw_user_meta_data->>'role', 'user')
  )
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ──────────────────────────────────────────────
-- TABELA: clientes
-- ──────────────────────────────────────────────
create table if not exists public.clientes (
  id              bigserial primary key,
  user_id         uuid not null references auth.users(id) on delete cascade,
  name            text not null,
  document_number text,            -- CNPJ ou CPF
  contact         text,            -- e-mail ou telefone
  responsible     text,            -- nome do responsável
  service_type    text default 'suporte'
                  check (service_type in ('suporte','infra','dev','consultoria','cftv','redes','outro')),
  status          text not null default 'ativo'
                  check (status in ('ativo','inativo','prospecto')),
  notes           text,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ──────────────────────────────────────────────
-- TABELA: equipamentos
-- ──────────────────────────────────────────────
create table if not exists public.equipamentos (
  id              bigserial primary key,
  user_id         uuid not null references auth.users(id) on delete cascade,
  name            text not null,
  type            text not null default 'outro',
  patrimony       text,
  serial_number   text,
  brand           text,
  model           text,
  responsible_user text,
  location        text,
  status          text not null default 'ativo'
                  check (status in ('ativo','inativo','manutencao','descartado')),
  purchase_date   timestamptz,
  warranty_until  timestamptz,
  notes           text,
  created_at      timestamptz default now(),
  updated_at      timestamptz default now()
);

-- ──────────────────────────────────────────────
-- TABELA: infraestrutura
-- dados_json armazena campos específicos por categoria
-- (ports, speed, va, watts, download, upload, etc.)
-- ──────────────────────────────────────────────
create table if not exists public.infraestrutura (
  id             bigserial primary key,
  user_id        uuid not null references auth.users(id) on delete cascade,
  name           text not null,
  category       text not null default 'servidor'
                 check (category in (
                   'servidor','switch','roteador','firewall','nobreak',
                   'access_point','storage','cloud','link','camera','outro'
                 )),
  ip_address     text,
  hostname       text,
  os             text,
  provider       text,
  location       text,
  cpu_cores      integer,
  ram_gb         numeric(8,2),
  disk_gb        numeric(10,2),
  monthly_cost   numeric(12,2),
  contract_until timestamptz,
  responsible    text,
  is_active      boolean default true,
  notes          text,
  -- Campos dinâmicos por categoria armazenados como JSONB
  -- Ex: {"ports":24,"speed":"1G","management":"gerenciavel"}
  -- Ex: {"va":1500,"watts":900,"autonomia":30}
  -- Ex: {"download":"500 Mbps","upload":"200 Mbps","isp":"Vivo"}
  dados_json       jsonb      default '{}'::jsonb,
  -- Monitoramento de conectividade (preenchido pelo frontend via ping)
  online_status    boolean    default null,   -- true=online, false=offline, null=não verificado
  last_checked_at  timestamptz default null,
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);

-- ──────────────────────────────────────────────
-- TABELA: topologia  (mapa Drawflow — 1 por user)
-- ──────────────────────────────────────────────
create table if not exists public.topologia (
  id            bigserial primary key,
  user_id       uuid not null references auth.users(id) on delete cascade,
  constraint topologia_user_id_unique unique (user_id),
  name          text default 'Topologia Principal',
  drawflow_data text,
  dados_json    jsonb default '{}'::jsonb,
  updated_at    timestamptz default now()
);

-- ──────────────────────────────────────────────
-- TABELA: softwares
-- ──────────────────────────────────────────────
create table if not exists public.softwares (
  id                bigserial primary key,
  user_id           uuid not null references auth.users(id) on delete cascade,
  name              text not null,
  version           text,
  license_key       text,
  license_type      text default 'assinatura',
  max_installations integer,
  vendor            text,
  valid_until       timestamptz,
  alert_days_before integer default 30,
  cost_monthly      numeric(12,2),
  notes             text,
  is_active         boolean default true,
  created_at        timestamptz default now(),
  updated_at        timestamptz default now()
);

-- ──────────────────────────────────────────────
-- TABELA: projetos
-- ──────────────────────────────────────────────
create table if not exists public.projetos (
  id             bigserial primary key,
  user_id        uuid not null references auth.users(id) on delete cascade,
  name           text not null,
  description    text,
  responsible    text,
  status         text not null default 'planejamento'
                 check (status in ('planejamento','em_andamento','pausado','concluido','cancelado')),
  progress       integer default 0 check (progress >= 0 and progress <= 100),
  start_date     timestamptz,
  end_date       timestamptz,
  repository_url text,
  production_url text,
  notes          text,
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);

-- ──────────────────────────────────────────────
-- TABELA: scripts
-- ──────────────────────────────────────────────
create table if not exists public.scripts (
  id          bigserial primary key,
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  language    text not null,
  description text,
  code        text not null,
  used_in     text,
  tags        text,
  version     text,
  author      text,
  is_active   boolean default true,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- ──────────────────────────────────────────────
-- TABELA: tecnologias
-- ──────────────────────────────────────────────
create table if not exists public.tecnologias (
  id          bigserial primary key,
  user_id     uuid not null references auth.users(id) on delete cascade,
  name        text not null,
  category    text not null,
  version     text,
  description text,
  docs_url    text,
  is_active   boolean default true,
  created_at  timestamptz default now()
);

-- ══════════════════════════════════════════════
-- ROW LEVEL SECURITY
-- ══════════════════════════════════════════════
do $$
declare t text;
begin
  foreach t in array array[
    'profiles','clientes','equipamentos','infraestrutura',
    'topologia','softwares','projetos','scripts','tecnologias'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "user_owns_%s" on public.%I', t, t);
  end loop;
end $$;

-- Função security definer: lê o role do usuário atual sem acionar RLS
-- (evita recursão infinita em políticas que consultam a própria tabela)
create or replace function public.get_my_role()
returns text
language sql
security definer
stable
as $$
  select role from public.profiles where id = auth.uid();
$$;

-- profiles: usuário vê/edita apenas o próprio; admin vê todos
create policy "user_owns_profiles" on public.profiles
  for all using (auth.uid() = id) with check (auth.uid() = id);

-- Política especial para admin ver todos os perfis (usa função, não subquery recursiva)
create policy "admin_reads_profiles" on public.profiles
  for select using (public.get_my_role() = 'admin');

-- Demais tabelas: isolamento por user_id
do $$
declare t text;
begin
  foreach t in array array[
    'clientes','equipamentos','infraestrutura',
    'topologia','softwares','projetos','scripts','tecnologias'
  ] loop
    execute format(
      'create policy "user_owns_%s" on public.%I
       for all using (auth.uid() = user_id) with check (auth.uid() = user_id)',
      t, t
    );
  end loop;
end $$;

-- ══════════════════════════════════════════════
-- TRIGGER updated_at
-- ══════════════════════════════════════════════
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

do $$
declare t text;
begin
  foreach t in array array[
    'profiles','clientes','equipamentos','infraestrutura',
    'topologia','softwares','projetos','scripts'
  ] loop
    execute format('drop trigger if exists trg_%I_updated_at on public.%I', t, t);
    execute format(
      'create trigger trg_%I_updated_at before update on public.%I
       for each row execute function public.set_updated_at()', t, t
    );
  end loop;
end $$;

-- ══════════════════════════════════════════════
-- ÍNDICES
-- ══════════════════════════════════════════════
create index if not exists idx_profiles_role         on public.profiles(role);
create index if not exists idx_clientes_user         on public.clientes(user_id);
create index if not exists idx_equipamentos_user     on public.equipamentos(user_id);
create index if not exists idx_infraestrutura_user   on public.infraestrutura(user_id);
create index if not exists idx_infraestrutura_cat    on public.infraestrutura(user_id, category);
create index if not exists idx_topologia_user        on public.topologia(user_id);
create index if not exists idx_softwares_user        on public.softwares(user_id);
create index if not exists idx_softwares_validade    on public.softwares(user_id, valid_until) where valid_until is not null;
create index if not exists idx_projetos_user         on public.projetos(user_id);
create index if not exists idx_scripts_user          on public.scripts(user_id);
create index if not exists idx_tecnologias_user      on public.tecnologias(user_id);
-- Índice GIN para buscas dentro do dados_json
create index if not exists idx_infraestrutura_json   on public.infraestrutura using gin(dados_json);

-- ══════════════════════════════════════════════
-- VÍNCULO CLIENTE ↔ EQUIPAMENTOS / INFRA
-- Permite filtrar ativos por cliente na tela de detalhes
-- ══════════════════════════════════════════════
alter table public.equipamentos
  add column if not exists client_id bigint
  references public.clientes(id) on delete set null;

alter table public.infraestrutura
  add column if not exists client_id bigint
  references public.clientes(id) on delete set null;

create index if not exists idx_equipamentos_client   on public.equipamentos(user_id, client_id);
create index if not exists idx_infraestrutura_client on public.infraestrutura(user_id, client_id);

-- ══════════════════════════════════════════════
-- VERIFICAÇÃO FINAL
-- ══════════════════════════════════════════════
select table_name,
  (select count(*) from information_schema.columns c
   where c.table_name = t.table_name and c.table_schema = 'public') as colunas
from information_schema.tables t
where table_schema = 'public'
  and table_name in (
    'profiles','clientes','equipamentos','infraestrutura',
    'topologia','softwares','projetos','scripts','tecnologias'
  )
order by table_name;
