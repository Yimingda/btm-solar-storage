-- ════════════════════════════════════════════════════════════════════
-- BTM PV+BESS Financial Modelling System — Supabase Setup SQL
-- Run this entire file in Supabase SQL Editor (once, on initial setup)
-- ════════════════════════════════════════════════════════════════════

-- ── 1. User Profiles ─────────────────────────────────────────────────
create table if not exists public.user_profiles (
    id                uuid primary key references auth.users(id) on delete cascade,
    email             text not null,
    full_name         text,
    company           text,
    tier              text not null default 'free'
                          check (tier in ('free', 'pro', 'admin')),
    snapshot_limit    integer not null default 3,
    is_active         boolean not null default true,
    created_at        timestamptz not null default now(),
    last_login        timestamptz,
    activated_by      uuid references public.user_profiles(id)
);

-- ── 2. Snapshots ─────────────────────────────────────────────────────
create table if not exists public.snapshots (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid not null references public.user_profiles(id) on delete cascade,
    name              text not null,
    default_name      text,
    params_json       jsonb not null default '{}'::jsonb,
    results_json      jsonb,
    is_pinned         boolean not null default false,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

-- ── 3. Audit Log ─────────────────────────────────────────────────────
create table if not exists public.audit_log (
    id                bigserial primary key,
    actor_id          uuid references public.user_profiles(id) on delete set null,
    action            text not null,
    target_id         uuid,
    detail            jsonb default '{}'::jsonb,
    created_at        timestamptz not null default now()
);

-- ── 4. Indexes ────────────────────────────────────────────────────────
create index if not exists idx_snapshots_user_id   on public.snapshots(user_id);
create index if not exists idx_snapshots_updated   on public.snapshots(updated_at desc);
create index if not exists idx_audit_log_actor     on public.audit_log(actor_id);
create index if not exists idx_audit_log_created   on public.audit_log(created_at desc);

-- ── 5. Row Level Security ─────────────────────────────────────────────
-- Users can read their own profile; admin operations bypass via service_role
alter table public.user_profiles enable row level security;
alter table public.snapshots      enable row level security;
alter table public.audit_log      enable row level security;

create policy "users_read_own_profile" on public.user_profiles
    for select using (auth.uid() = id);

create policy "users_read_own_snapshots" on public.snapshots
    for select using (auth.uid() = user_id);

-- All write operations use service_role key (bypasses RLS) — no user policies needed

-- ── 6. Auto-create profile on signup (Trigger) ───────────────────────
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
declare
    v_is_admin  boolean;
    v_tier      text;
    v_limit     integer;
begin
    -- Hard-coded admin email (change if needed)
    v_is_admin := (new.email = 'zhaoqiongling@gmail.com');
    v_tier     := case when v_is_admin then 'admin' else 'free' end;
    v_limit    := case when v_is_admin then 999999  else 3      end;

    insert into public.user_profiles
        (id, email, full_name, company, tier, snapshot_limit)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', ''),
        coalesce(new.raw_user_meta_data->>'company',   ''),
        v_tier,
        v_limit
    )
    on conflict (id) do nothing;  -- idempotent

    return new;
end;
$$;

-- Attach trigger (drop first to allow re-running this script)
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ── 7. Verify setup ───────────────────────────────────────────────────
-- Run this to confirm tables exist:
-- select table_name from information_schema.tables
--   where table_schema = 'public'
--   order by table_name;
