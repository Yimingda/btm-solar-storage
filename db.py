"""
db.py — Supabase 数据库操作封装
BTM PV+BESS Financial Modelling System

All database interactions go through this module.
Two clients:
  • anon   — subject to Row Level Security (for auth operations)
  • admin  — uses service_role key, bypasses RLS (for data reads/writes)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import streamlit as st


# ── Client factory ──────────────────────────────────────────────────────────

def _secrets_ok() -> bool:
    try:
        _ = st.secrets["supabase"]["url"]
        return True
    except Exception:
        return False


@st.cache_resource
def _anon_client():
    from supabase import create_client
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["anon_key"],
    )


@st.cache_resource
def _admin_client():
    from supabase import create_client
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["service_role_key"],
    )


def get_db():
    """Anon client — for auth calls that follow Supabase Auth rules."""
    if not _secrets_ok():
        return None
    return _anon_client()


def get_admin_db():
    """Service-role client — bypasses RLS, for all data operations."""
    if not _secrets_ok():
        return None
    return _admin_client()


# ── Auth ────────────────────────────────────────────────────────────────────

def sign_up(email: str, password: str, full_name: str, company: str):
    """Register a new user. Supabase sends OTP verification email automatically."""
    db = get_db()
    return db.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {
                "full_name": full_name,
                "company":   company,
            }
        },
    })


def verify_otp(email: str, token: str):
    """Verify signup with the 6-digit OTP from the verification email."""
    db = get_db()
    return db.auth.verify_otp({
        "email": email,
        "token": token,
        "type":  "signup",
    })


def sign_in(email: str, password: str):
    """Sign in with email + password. Returns AuthResponse."""
    db = get_db()
    return db.auth.sign_in_with_password({"email": email, "password": password})


def sign_out():
    db = get_db()
    if db:
        try:
            db.auth.sign_out()
        except Exception:
            pass


def resend_verification(email: str):
    db = get_db()
    return db.auth.resend({"type": "signup", "email": email})


# ── User Profile ─────────────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> Optional[dict]:
    """Fetch user_profiles row. Uses admin client to always get data."""
    try:
        db = get_admin_db()
        res = (db.table("user_profiles")
                 .select("*")
                 .eq("id", user_id)
                 .maybe_single()
                 .execute())
        return res.data
    except Exception:
        return None


def update_last_login(user_id: str) -> None:
    try:
        db = get_admin_db()
        db.table("user_profiles").update({
            "last_login": datetime.now(timezone.utc).isoformat(),
        }).eq("id", user_id).execute()
    except Exception:
        pass


# ── Snapshots ───────────────────────────────────────────────────────────────

def get_snapshots(user_id: str) -> list[dict]:
    """All snapshots for user, sorted: pinned first, then newest first."""
    try:
        db = get_admin_db()
        res = (db.table("snapshots")
                 .select("id, name, default_name, results_json, is_pinned, created_at, updated_at")
                 .eq("user_id", user_id)
                 .order("is_pinned", desc=True)
                 .order("updated_at",  desc=True)
                 .execute())
        return res.data or []
    except Exception:
        return []


def get_snapshot_full(snapshot_id: str) -> Optional[dict]:
    """Fetch full snapshot row including params_json."""
    try:
        db = get_admin_db()
        res = (db.table("snapshots")
                 .select("*")
                 .eq("id", snapshot_id)
                 .maybe_single()
                 .execute())
        return res.data
    except Exception:
        return None


def save_snapshot(user_id: str, name: str, default_name: str,
                  params: dict, results: dict) -> Optional[dict]:
    try:
        db = get_admin_db()
        res = db.table("snapshots").insert({
            "user_id":      user_id,
            "name":         name,
            "default_name": default_name,
            "params_json":  params,
            "results_json": results,
            "updated_at":   datetime.now(timezone.utc).isoformat(),
        }).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        st.error(f"Save failed / 保存失败: {e}")
        return None


def update_snapshot(snapshot_id: str, **kwargs) -> bool:
    """Update any snapshot fields. Always sets updated_at."""
    try:
        db = get_admin_db()
        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        db.table("snapshots").update(kwargs).eq("id", snapshot_id).execute()
        return True
    except Exception:
        return False


def delete_snapshot(snapshot_id: str) -> bool:
    try:
        db = get_admin_db()
        db.table("snapshots").delete().eq("id", snapshot_id).execute()
        return True
    except Exception:
        return False


def count_snapshots(user_id: str) -> int:
    try:
        db = get_admin_db()
        res = (db.table("snapshots")
                 .select("id", count="exact")
                 .eq("user_id", user_id)
                 .execute())
        return res.count or 0
    except Exception:
        return 0


# ── Admin Operations ─────────────────────────────────────────────────────────

def get_all_users() -> list[dict]:
    try:
        db = get_admin_db()
        res = (db.table("user_profiles")
                 .select("*")
                 .order("created_at", desc=True)
                 .execute())
        return res.data or []
    except Exception:
        return []


def update_user_tier(user_id: str, tier: str, snapshot_limit: int,
                     actor_id: str) -> bool:
    try:
        db = get_admin_db()
        db.table("user_profiles").update({
            "tier":           tier,
            "snapshot_limit": snapshot_limit,
            "activated_by":   actor_id,
        }).eq("id", user_id).execute()
        db.table("audit_log").insert({
            "actor_id":  actor_id,
            "action":    "tier_change",
            "target_id": user_id,
            "detail":    {"tier": tier, "snapshot_limit": snapshot_limit},
        }).execute()
        return True
    except Exception:
        return False


def set_user_active(user_id: str, is_active: bool, actor_id: str) -> bool:
    try:
        db = get_admin_db()
        db.table("user_profiles").update(
            {"is_active": is_active}
        ).eq("id", user_id).execute()
        db.table("audit_log").insert({
            "actor_id":  actor_id,
            "action":    "activate" if is_active else "suspend",
            "target_id": user_id,
            "detail":    {},
        }).execute()
        return True
    except Exception:
        return False


def get_audit_log(limit: int = 100) -> list[dict]:
    try:
        db = get_admin_db()
        res = (db.table("audit_log")
                 .select("*, user_profiles!actor_id(email, full_name)")
                 .order("created_at", desc=True)
                 .limit(limit)
                 .execute())
        return res.data or []
    except Exception:
        return []


def get_system_stats() -> dict:
    try:
        db = get_admin_db()
        users = get_all_users()
        snap_res = db.table("snapshots").select("id", count="exact").execute()
        return {
            "total_users": len(users),
            "free_users":  sum(1 for u in users if u.get("tier") == "free"),
            "pro_users":   sum(1 for u in users if u.get("tier") == "pro"),
            "admin_users": sum(1 for u in users if u.get("tier") == "admin"),
            "total_snaps": snap_res.count or 0,
        }
    except Exception:
        return {}
