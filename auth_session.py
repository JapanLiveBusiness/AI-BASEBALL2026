"""Auth0 login helpers and per-user storage routing."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
from typing import Any, Mapping

import streamlit as st


AUTH_PROVIDER = "auth0"
AUTH_ENABLED_ENV = "AI_BASEBALL_AUTH_ENABLED"


@dataclass(frozen=True)
class AuthUser:
    subject: str
    name: str
    email: str
    authenticated: bool

    @property
    def display_name(self) -> str:
        return self.name or self.email or "ログインユーザー"


def auth0_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether the deployment has mounted its Auth0 configuration."""
    values = os.environ if environ is None else environ
    return str(values.get(AUTH_ENABLED_ENV, "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _claim(user: Any, key: str) -> str:
    try:
        value = user.get(key, "")
    except (AttributeError, TypeError):
        try:
            value = user[key]
        except (KeyError, TypeError):
            value = ""
    return str(value or "").strip()


def user_from_claims(claims: Mapping[str, Any]) -> AuthUser:
    """Build the application identity from validated OIDC identity claims."""
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise ValueError("Auth0のユーザー識別子を確認できません。")
    return AuthUser(
        subject=subject,
        name=str(claims.get("name") or "").strip(),
        email=str(claims.get("email") or "").strip(),
        authenticated=True,
    )


def require_auth0() -> AuthUser:
    """Require Auth0 when configured, with a safe legacy mode before activation."""
    if not auth0_enabled():
        return AuthUser(
            subject="legacy-single-user",
            name="現行利用者",
            email="",
            authenticated=False,
        )

    if not bool(getattr(st.user, "is_logged_in", False)):
        st.title("AI BASEBALL STUDIO")
        st.write("BET履歴と分析データを開くにはAuth0でログインしてください。")
        if st.button("Auth0でログイン", type="primary", width="stretch"):
            st.login(AUTH_PROVIDER)
        st.stop()

    try:
        user = user_from_claims(
            {
                "sub": _claim(st.user, "sub"),
                "name": _claim(st.user, "name"),
                "email": _claim(st.user, "email"),
            }
        )
    except ValueError as exc:
        st.error(str(exc))
        if st.button("ログアウトして再試行"):
            st.logout()
        st.stop()
    return user


def user_storage_key(subject: str) -> str:
    """Create a filesystem-safe opaque key without exposing the Auth0 subject."""
    normalized = str(subject or "").strip()
    if not normalized:
        raise ValueError("ユーザー識別子が空です。")
    return sha256(f"auth0:{normalized}".encode("utf-8")).hexdigest()[:32]


def user_bets_path(data_dir: Path, user: AuthUser) -> Path:
    """Route authenticated users to isolated files and retain pre-Auth0 data."""
    base = Path(data_dir)
    if not user.authenticated:
        return base / "bet_records.json"
    return base / "users" / user_storage_key(user.subject) / "bet_records.json"


def render_account_controls(user: AuthUser) -> None:
    """Show the active Auth0 identity and an application-session logout control."""
    if not user.authenticated:
        return
    account = st.container(horizontal=True, horizontal_alignment="right")
    identity = user.email or user.display_name
    account.caption(f":material/account_circle: {identity}")
    if account.button("ログアウト", key="auth0_logout", icon=":material/logout:"):
        st.logout()
