from __future__ import annotations

import os

import streamlit as st

ALLOWED_EMAILS = {
    email.strip().lower()
    for email in os.getenv(
        "AUTH_ALLOWED_EMAILS",
        "tsutsumi@japanlivebusiness.com,tsutsumi41@gmail.com",
    ).split(",")
    if email.strip()
}


def _user_email() -> str:
    try:
        return str(st.user.get("email") or "").strip().lower()
    except Exception:
        return ""


def require_login() -> None:
    """Require Clerk OIDC login and restrict access to the configured email allowlist."""
    try:
        logged_in = bool(st.user.is_logged_in)
    except Exception:
        logged_in = False

    if not logged_in:
        st.markdown(
            """
<style>
[data-testid="stHeader"],[data-testid="stToolbar"],footer{display:none!important}
[data-testid="stAppViewContainer"]{background:#080b0e!important;color:#f4f6f8!important}
.block-container{max-width:520px!important;padding-top:11vh!important}
.login-shell{background:linear-gradient(180deg,#12171d,#0d1115);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:28px 30px 20px;box-shadow:0 24px 70px rgba(0,0,0,.35);margin-bottom:14px}
.login-brand{display:flex;align-items:center;gap:12px;margin-bottom:18px}.login-logo{width:44px;height:44px;border:2px solid #f0b82f;border-radius:50%;display:grid;place-items:center;color:#f0b82f;font-size:18px}.login-title{font-size:18px;font-weight:950;color:#f0b82f}.login-sub{font-size:9px;color:#9098a2;margin-top:3px}.login-copy{font-size:11px;color:#b7bec7;line-height:1.7;border-top:1px solid rgba(255,255,255,.08);padding-top:15px}
</style>
<div class="login-shell"><div class="login-brand"><div class="login-logo">⚾</div><div><div class="login-title">AI BASEBALL STUDIO</div><div class="login-sub">CLERK PRIVATE LOGIN</div></div></div><div class="login-copy">この研究サイトを閲覧するにはClerk認証が必要です。Googleアカウントでログインしてください。</div></div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Clerkでログイン", type="primary", use_container_width=True):
            try:
                st.login("clerk")
            except Exception:
                st.error("Clerk OIDC設定がまだ完了していません。管理者が接続情報を設定してください。")
        st.stop()

    email = _user_email()
    if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
        st.error("このアカウントにはAI BASEBALL STUDIOの閲覧権限がありません。")
        if st.button("ログアウト"):
            st.logout()
        st.stop()


def current_username() -> str:
    try:
        return _user_email() or str(st.user.get("name") or "Clerk user")
    except Exception:
        return "Clerk user"


def logout() -> None:
    st.logout()
