"""
Página de Busca — free-text query contra a API (lexical + semantic).
Enhanced with semantic search, similar characters, and cross-novel search.
"""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from app.dashboard.api_client import get

logger = logging.getLogger(__name__)


def _render_search_results(hits: list[dict], total: int) -> None:
    """Render search results with kind filter and export."""
    if not hits:
        st.warning("Nenhum resultado encontrado.")
        return

    kinds = sorted({h.get("kind", "unknown") for h in hits})
    selected = st.multiselect("Filtrar por tipo", kinds, default=kinds, key="search_filter")
    filtered = [h for h in hits if h.get("kind", "unknown") in selected]

    st.subheader(f"Resultados ({len(filtered)} / {total})")

    for h in filtered:
        kind_icon = {"character": "⚔️", "organization": "🏛️", "location": "📍", "novel": "📘"}.get(
            h.get("kind", ""), "❓"
        )
        with st.container(border=True):
            cols = st.columns([5, 1])
            with cols[0]:
                name = h.get("name") or h.get("canonical_name", "Unknown")
                st.markdown(f"{kind_icon} **{name}** _({h.get('kind', 'unknown')})_")
                if h.get("description"):
                    st.caption(h["description"][:200])
                elif h.get("snippet"):
                    st.caption(h["snippet"][:200])
            with cols[1]:
                st.metric("Score", f"{h.get('score', 0):.2f}")

    df = pd.DataFrame(
        [
            {
                "name": h.get("name") or h.get("canonical_name", ""),
                "kind": h.get("kind", "unknown"),
                "score": round(h.get("score", 0), 3),
            }
            for h in filtered
        ]
    )
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Exportar CSV",
        data=csv_data,
        file_name="search_results.csv",
        mime="text/csv",
        key="export_search",
    )


def _tab_lexical_semantic() -> None:
    """Lexical + semantic search tab."""
    col_q, col_sem, _ = st.columns([3, 1, 2])
    with col_q:
        query = st.text_input(
            "Digite o termo de busca",
            key="search_query",
            placeholder="ex: Murim, Sword, Sect...",
        )
    with col_sem:
        semantic = st.toggle("Semântica", value=False, key="search_semantic")

    if not query:
        st.info("Digite um termo para iniciar a busca.")
        return

    with st.spinner("Buscando..."):
        try:
            results = get(
                "api/v1/search",
                params={"q": query, "limit": 50, "semantic": semantic},
            )
        except Exception as exc:
            logger.warning("Search query failed: %s", exc)
            st.error("Erro ao executar a busca. Verifique se a API está no ar.")
            return

    _render_search_results(results.get("hits", []), results.get("total", 0))


def _tab_semantic() -> None:
    """Dedicated semantic search tab using the new /search/semantic endpoint."""
    query = st.text_input(
        "Busca semântica (vetorial)",
        key="semantic_query",
        placeholder="ex: powerful swordsman, sect leader, ancient technique...",
    )
    limit = st.slider("Limite de resultados", 5, 100, 20, key="semantic_limit")

    if not query:
        st.info("Digite uma consulta para busca semântica.")
        return

    with st.spinner("Buscando por similaridade vetorial..."):
        try:
            results = get(
                "api/v1/search/semantic",
                params={"q": query, "limit": limit},
            )
        except Exception as exc:
            logger.warning("Semantic search failed: %s", exc)
            st.error("Erro na busca semântica. Verifique se a API está no ar.")
            return

    search_type = results.get("search_type", "unknown")
    st.caption(f"Tipo de busca: {search_type}")

    hits = [
        {
            "name": r.get("name") or r.get("canonical_name", ""),
            "kind": r.get("kind", "character"),
            "score": r.get("score", 0),
            "description": r.get("description", ""),
            "canonical_name": r.get("canonical_name", ""),
        }
        for r in results.get("results", [])
    ]
    _render_search_results(hits, results.get("total", 0))


def _tab_similar_characters() -> None:
    """Find similar characters tab."""
    col_id, col_thresh = st.columns([3, 1])
    with col_id:
        character_id = st.text_input(
            "ID do personagem",
            key="similar_char_id",
            placeholder="UUID do personagem",
        )
    with col_thresh:
        threshold = st.slider("Limiar de similaridade", 0.0, 1.0, 0.3, key="similar_threshold")
    limit = st.slider("Limite", 1, 50, 10, key="similar_limit")

    if not character_id:
        st.info("Insira o UUID de um personagem para encontrar similares.")
        return

    with st.spinner("Buscando personagens similares..."):
        try:
            results = get(
                f"api/v1/search/similar/{character_id}",
                params={"limit": limit, "threshold": threshold},
            )
        except Exception as exc:
            logger.warning("Similar characters query failed: %s", exc)
            st.error("Erro ao buscar similares. Verifique o ID e a API.")
            return

    char_name = results.get("character_name", "Unknown")
    st.subheader(f"Personagens similares a: **{char_name}**")

    similar = results.get("similar_characters", [])
    if not similar:
        st.warning("Nenhum personagem similar encontrado.")
        return

    for s in similar:
        with st.container(border=True):
            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(f"⚔️ **{s.get('name', 'Unknown')}**")
                if s.get("canonical_name"):
                    st.caption(f"Canônico: {s['canonical_name']}")
            with cols[1]:
                st.metric("Score", f"{s.get('score', 0):.2f}")


def _tab_cross_novel() -> None:
    """Cross-novel search tab."""
    query = st.text_input(
        "Busca cross-novel",
        key="cross_novel_query",
        placeholder="Busque em todos os novels...",
    )
    limit = st.slider("Limite", 5, 200, 50, key="cross_novel_limit")

    if not query:
        st.info("Digite uma consulta para buscar em todos os novels.")
        return

    with st.spinner("Buscando cross-novel..."):
        try:
            results = get(
                "api/v1/search/cross-novel",
                params={"q": query, "limit": limit},
            )
        except Exception as exc:
            logger.warning("Cross-novel search failed: %s", exc)
            st.error("Erro na busca cross-novel.")
            return

    hits = [
        {
            "name": r.get("name") or r.get("canonical_name", ""),
            "kind": r.get("kind", "character"),
            "score": r.get("score", 0),
            "description": r.get("description", ""),
        }
        for r in results.get("results", [])
    ]
    _render_search_results(hits, results.get("total", 0))


def show() -> None:
    st.title("Busca")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔍 Lexical/Semântica", "🧠 Semântica", "👤 Similares", "📚 Cross-Novel"]
    )

    with tab1:
        _tab_lexical_semantic()
    with tab2:
        _tab_semantic()
    with tab3:
        _tab_similar_characters()
    with tab4:
        _tab_cross_novel()
