"""
Visão Geral — métricas, cards de estatísticas e resumo dos últimos dados.
"""
from __future__ import annotations

import time

import plotly.express as px
import streamlit as st

from app.dashboard.api_client import get, post


def show() -> None:
    st.title("🏠 Visão Geral")
    st.caption("Dashboard do Murim Knowledge Base — rápido resumo do estado do sistema.")

    # ── KPIs ──
    try:
        novels = get("api/v1/novels", params={"limit": 1})
        total_novels = novels["meta"]["total"]
    except Exception:
        total_novels = 0
    try:
        chars = get("api/v1/characters", params={"limit": 1})
        total_chars = chars["meta"]["total"]
    except Exception:
        total_chars = 0
    try:
        orgs = get("api/v1/organizations", params={"limit": 1})
        total_orgs = orgs["meta"]["total"]
    except Exception:
        total_orgs = 0
    try:
        graph_info = get("api/v1/graph")
        graph_size = graph_info["stats"]
    except Exception:
        graph_size = {"nodes": 0, "edges": 0}

    kpi = st.columns(4)
    with kpi[0]:
        st.metric("Novels", f"{total_novels}")
    with kpi[1]:
        st.metric("Personagens", f"{total_chars}")
    with kpi[2]:
        st.metric("Organizações", f"{total_orgs}")
    with kpi[3]:
        st.metric("Grafo (nós)", f"{graph_size.get('nodes', 0)}")

    st.divider()

    # ── Recent content ──
    col_left, col_right = st.columns([2, 1])

    with col_right:
        st.subheader("➕ Inserção Rápida")
        with st.form("quick_add"):
            kind = st.selectbox("Tipo", ["Novel", "Personagem", "Organização"])
            submitted = False
            if kind == "Novel":
                title = st.text_input("Título", key="qa_title")
                if st.form_submit_button("Adicionar") and title:
                    try:
                        post("api/v1/novels", json={"title": title, "language": "en"})
                        st.success("Novel adicionada!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception:
                        st.warning("Erro ao adicionar novel")
            elif kind == "Personagem":
                name = st.text_input("Nome", key="qa_char_name")
                if st.form_submit_button("Adicionar") and name:
                    try:
                        post("api/v1/characters", json={"name": name})
                        st.success("Personagem adicionado!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception:
                        st.warning("Erro ao adicionar personagem")
            elif kind == "Organização":
                name = st.text_input("Nome", key="qa_org_name")
                org_type = st.text_input("Tipo (ex: Sect)", key="qa_org_type")
                if st.form_submit_button("Adicionar") and name and org_type:
                    try:
                        post("api/v1/organizations", json={"name": name, "type": org_type})
                        st.success("Organização adicionada!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception:
                        st.warning("Erro ao adicionar organização")

    with col_left:
        st.subheader("📊 Distribuição por Tipo (Grafo)")
        if graph_size.get("nodes", 0) > 0:
            _render_graph_summary()
        else:
            st.info("Nenhum dado no grafo. Ingeste capítulos ou entidades para visualizar.")

        st.subheader("📰 Dados Recentes")
        tabs = st.tabs(["Novels", "Personagens", "Organizações"])

        # Novels
        with tabs[0]:
            try:
                data = get("api/v1/novels", params={"limit": 5})
                _render_table(data["items"], ["title", "author", "total_chapters"],
                              ["Título", "Autor", "Chap."])
            except Exception:
                st.info("Nenhuma novel cadastrada.")

        # Characters
        with tabs[1]:
            try:
                data = get("api/v1/characters", params={"limit": 5})
                _render_table(data["items"], ["name", "canonical_name", "appearance_frequency"],
                              ["Nome", "Canonical", "Freq."])
            except Exception:
                st.info("Nenhum personagem cadastrado.")

        # Organizations
        with tabs[2]:
            try:
                data = get("api/v1/organizations", params={"limit": 5})
                _render_table(data["items"], ["name", "type"],
                              ["Nome", "Tipo"])
            except Exception:
                st.info("Nenhuma organização cadastrada.")


def _render_graph_summary() -> None:
    try:
        graph_info = get("api/v1/graph")
        stats = graph_info.get("stats", {})
        labels = ["Characters", "Organizations", "Locations"]
        values = [stats.get("characters", 0), stats.get("organizations", 0), stats.get("locations", 0)]
        fig = px.pie(names=labels, values=values, hole=0.4, title="Nós no Grafo")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True, key="graph_summary_pie")
    except Exception:
        st.info("Nenhum dado no grafo.")


def _render_table(items, keys, labels):
    if not items:
        st.info("Sem dados.")
        return

    import pandas as pd
    rows = [{label: item.get(k, "") for k, label in zip(keys, labels)} for item in items]
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
