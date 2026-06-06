"""
Página de Personagens — listagem, filtros e detalhes.
"""
from __future__ import annotations

import streamlit as st

from app.dashboard.api_client import get


def show() -> None:
    st.title("⚔️ Personagens")

    col_filter, col_list = st.columns([2, 5])

    with col_filter:
        search_query = st.text_input("Buscar por nome", "")

    with col_list:
        try:
            if search_query:
                st.info("O endpoint de busca por substring ainda não é paginado. Mostrando personagens sem filtro.")
            data = get("api/v1/characters", params={"limit": 100})
            items = data.get("items", [])
        except Exception:
            items = []

        if not items:
            st.info("Nenhum personagem cadastrado.")
            return

        for char in items:
            with st.container(border=True):
                name_col, freq_col = st.columns([4, 1])
                with name_col:
                    st.markdown(f"**{char.get('name', '???')}** «{char.get('canonical_name', '')}»")
                    if char.get("description"):
                        st.caption(char["description"][:120] + "…")
                with freq_col:
                    st.metric("Freq.", char.get("appearance_frequency", 0))
