"""
Página de Personagens — busca funcional, CRUD completo, paginação.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.dashboard.api_client import delete, get, patch


def show() -> None:
    st.title("⚔️ Personagens")

    # ── Controles ──
    col_search, col_page, col_export = st.columns([3, 2, 1])

    with col_search:
        query = st.text_input(
            "Buscar por nome", key="char_search", placeholder="Digite para filtrar..."
        )
    with col_page:
        limit_options = [10, 25, 50, 100]
        per_page = st.selectbox("Por página", limit_options, index=1, key="char_pp")
        page = st.number_input("Página", min_value=1, value=1, key="char_page")

    # ── Dados ──
    try:
        if query.strip():
            data = get("api/v1/search", params={"q": query, "limit": 200})
            all_items = [h for h in data.get("hits", []) if h.get("kind") == "character"]
        else:
            data = get(
                "api/v1/characters", params={"limit": per_page, "offset": (page - 1) * per_page}
            )
            all_items = data.get("items", [])
            total_count = data.get("meta", {}).get("total", 0)
    except Exception:
        st.warning("Erro ao carregar dados da API.")
        return

    total_count = data.get("meta", {}).get("total", len(all_items))
    total_pages = max(1, (total_count + per_page - 1) // per_page) if not query.strip() else 1

    st.caption(f"{total_count} personagem(ns) encontrado(s). Página {page} / {total_pages}")

    with col_export:
        _render_export_button(all_items, "personagens")

    if not all_items:
        st.info("Nenhum personagem encontrado.")
        return

    # ── Listagem ──
    for char in all_items:
        with st.container(border=True):
            _render_character_row(char)


def _render_character_row(char: dict) -> None:
    cid = char.get("id", "")
    name = char.get("name", "???")
    canonical = char.get("canonical_name", "")

    with st.expander(f"{name} «{canonical}»", expanded=False):
        col_info, col_actions = st.columns([3, 1])

        with col_info:
            st.markdown(f"**ID:** `{cid}`")
            st.markdown(f"**Nome:** {name}")
            st.markdown(f"**Canonical:** {canonical}")
            if char.get("gender"):
                st.markdown(f"**Gênero:** {char['gender']}")
            if char.get("description"):
                st.markdown(
                    f"**Descrição:** {char['description'][:200]}{'…' if len(char.get('description', '')) > 200 else ''}"
                )
            st.markdown(f"**Frequência:** {char.get('appearance_frequency', 0)}")
            aliases = char.get("aliases", [])
            if aliases:
                alias_str = ", ".join(f"{a['alias_type']}: {a['alias_value']}" for a in aliases)
                st.markdown(f"**Aliases:** {alias_str}")
            titles = char.get("titles", [])
            if titles:
                st.markdown(f"**Títulos:** {', '.join(titles)}")
            orgs = char.get("organizations", [])
            if orgs:
                st.markdown(f"**Organizações:** {', '.join(orgs)}")
            locs = char.get("locations", [])
            if locs:
                st.markdown(f"**Localizações:** {', '.join(locs)}")
            rels = char.get("relationships", {})
            if rels:
                rel_str = "; ".join(f"{k}: {', '.join(v)}" for k, v in rels.items())
                st.markdown(f"**Relacionamentos:** {rel_str}")
            embedding_status = "✅" if char.get("has_embedding") else "❌"
            st.markdown(f"**Embedding:** {embedding_status}")

        with col_actions:
            edit_mode = st.checkbox("Editar", key=f"edit_{cid}")
            if edit_mode:
                with st.form(key=f"form_{cid}"):
                    new_name = st.text_input("Nome", value=name, key=f"nm_{cid}")
                    new_gender = st.selectbox(
                        "Gênero",
                        ["", "Male", "Female", "Other"],
                        index=0
                        if not char.get("gender")
                        else ["", "Male", "Female", "Other"].index(char.get("gender", "")),
                        key=f"gd_{cid}",
                    )
                    new_desc = st.text_area(
                        "Descrição", value=char.get("description") or "", key=f"ds_{cid}"
                    )
                    if st.form_submit_button("Salvar"):
                        try:
                            patch(
                                f"api/v1/characters/{cid}",
                                json={
                                    "name": new_name,
                                    "gender": new_gender if new_gender else None,
                                    "description": new_desc if new_desc else None,
                                },
                            )
                            st.success("Salvo!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro: {exc}")

            confirm_delete = st.checkbox("🗑️ Deletar", key=f"del_{cid}")
            if confirm_delete and st.button(
                f"Confirmar exclusão de {name}", key=f"btndel_{cid}", type="primary"
            ):
                try:
                    delete(f"api/v1/characters/{cid}")
                    st.success(f"{name} deletado!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro: {exc}")


def _render_export_button(items: list, name: str) -> None:
    if not items:
        return
    df = pd.DataFrame(
        [{k: v for k, v in item.items() if not isinstance(v, (list, dict))} for item in items]
    )

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ CSV",
        data=csv_data,
        file_name=f"{name}.csv",
        mime="text/csv",
        key=f"export_{name}",
    )
