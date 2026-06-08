"""
Página de Busca — free-text query contra a API (lexical + semantic).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.dashboard.api_client import get


def show() -> None:
    st.title("Busca")

    col_q, col_sem, _ = st.columns([3, 1, 2])
    with col_q:
        query = st.text_input(
            "Digite o termo de busca", key="search_query", placeholder="ex: Murim, Sword, Sect..."
        )
    with col_sem:
        semantic = st.toggle("Semântica", value=False, key="search_semantic")

    if not query:
        st.info("Digite um termo para iniciar a busca.")
        return

    with st.spinner("Buscando..."):
        try:
            results = get("api/v1/search", params={"q": query, "limit": 50, "semantic": semantic})
        except Exception:
            st.error("Erro ao executar a busca. Verifique se a API está no ar.")
            return

    hits = results.get("hits", [])
    total = results.get("total", 0)

    if not hits:
        st.warning("Nenhum resultado encontrado.")
        return

    # Filtro por kind
    kinds = sorted({h["kind"] for h in hits})
    selected = st.multiselect("Filtrar por tipo", kinds, default=kinds, key="search_filter")
    filtered = [h for h in hits if h["kind"] in selected]

    st.subheader(f"Resultados ({len(filtered)} / {total})")

    for h in filtered:
        kind_icon = {"character": "⚔️", "organization": "🏛️", "location": "📍", "novel": "📘"}.get(
            h["kind"], "❓"
        )
        with st.container(border=True):
            cols = st.columns([5, 1])
            with cols[0]:
                st.markdown(f"{kind_icon} **{h['name']}** _({h['kind']})_")
                if h.get("snippet"):
                    st.caption(h["snippet"][:200])
            with cols[1]:
                st.metric("Score", f"{h['score']:.2f}")

    # Export
    df = pd.DataFrame(
        [{"name": h["name"], "kind": h["kind"], "score": round(h["score"], 3)} for h in filtered]
    )
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Exportar CSV",
        data=csv_data,
        file_name=f"search_{query[:20]}.csv",
        mime="text/csv",
        key="export_search",
    )
