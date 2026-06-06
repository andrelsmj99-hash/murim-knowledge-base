"""
Página de Busca — free-text query contra a API (lexical + semantic).
"""
from __future__ import annotations

import streamlit as st

from app.dashboard.api_client import get


def show() -> None:
    st.title("Busca")

    query = st.text_input("Digite o termo de busca", "")
    semantic = st.toggle("Busca semântica (embeddings)", value=False)

    if not query:
        st.info("Digite um termo para iniciar a busca.")
        return

    with st.spinner("Buscando..."):
        try:
            results = get("api/v1/search", params={"q": query, "limit": 20, "semantic": semantic})
        except Exception:
            st.error("Erro ao executar a busca. Verifique se a API está no ar.")
            return

    hits = results.get("hits", [])
    st.subheader(f"Resultados ({results.get('total', 0)})")

    if not hits:
        st.warning("Nenhum resultado encontrado.")
        return

    for h in hits:
        with st.container(border=True):
            st.markdown(f"**{h['name']}** _({h['kind']})_ — score: {h['score']:.2f}")
