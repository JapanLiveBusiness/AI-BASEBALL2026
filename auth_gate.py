"""Authentication gate for the Streamlit application.

Authentication is provided by Streamlit's built-in OIDC support. Provider
credentials live in .streamlit/secrets.toml or deployment secrets and must
never be committed to the repository.
"""

import streamlit as st


def require_login() -> None:
    """Stop the app until the visitor has authenticated with Auth0."""
    if not st.user.is_logged_in:
        st.title("HAWKS AI")
        st.caption("AI-BASEBALL2026")
        st.info("このサイトを利用するにはログインしてください。")
        if st.button("ログイン", type="primary", use_container_width=True):
            st.login("auth0")
        st.stop()


def render_account_controls() -> None:
    """Render compact account information and a logout control."""
    name = getattr(st.user, "name", None) or getattr(st.user, "email", None) or "ログイン中"
    with st.sidebar:
        st.caption(str(name))
        if st.button("ログアウト", use_container_width=True):
            st.logout()
