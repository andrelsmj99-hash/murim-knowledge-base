"""
Novels — comparative statistics page.
"""

from __future__ import annotations

import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.api_client import get

logger = logging.getLogger(__name__)


def show() -> None:
    st.title("📚 Novels")
    st.caption("Estatísticas comparativas entre novels.")

    # Fetch novels list
    try:
        data = get("api/v1/novels", params={"limit": 100})
        novels = data.get("items", [])
    except Exception:
        logger.debug("Failed to fetch novels", exc_info=True)
        novels = []

    if not novels:
        st.info("Nenhuma novel encontrada.")
        return

    # Fetch stats for each novel
    stats_list = []
    for novel in novels:
        try:
            stats = get(f"api/v1/novels/{novel['id']}/stats")
            stats_list.append(stats)
        except Exception:
            logger.debug("Failed to fetch stats for %s", novel["id"], exc_info=True)
            stats_list.append(
                {
                    "novel_id": novel["id"],
                    "title": novel.get("title", "?"),
                    "chapters": 0,
                    "total_chapters_expected": 0,
                    "characters": 0,
                    "organizations": 0,
                    "locations": 0,
                    "relationships": 0,
                }
            )

    if not stats_list:
        st.warning("Não foi possível carregar estatísticas.")
        return

    df = pd.DataFrame(stats_list)

    # ── KPIs ──
    kpi = st.columns(4)
    with kpi[0]:
        st.metric("Novels", len(df))
    with kpi[1]:
        st.metric("Total Capítulos", int(df["chapters"].sum()))
    with kpi[2]:
        st.metric("Total Personagens (global)", int(df["characters"].max()))
    with kpi[3]:
        st.metric("Total Orgs (global)", int(df["organizations"].max()))

    st.divider()

    # ── Bar chart: chapters per novel ──
    st.subheader("Capítulos por Novel")
    fig_chapters = px.bar(
        df,
        x="title",
        y="chapters",
        color="title",
        text_auto=True,
        labels={"title": "Novel", "chapters": "Capítulos"},
    )
    fig_chapters.update_layout(showlegend=False)
    st.plotly_chart(fig_chapters, use_container_width=True)

    # ── Radar chart: comparative ──
    if len(df) > 1:
        st.subheader("Comparação Multidimensional")
        categories = ["chapters", "total_chapters_expected"]
        fig_radar = go.Figure()
        for _, row in df.iterrows():
            fig_radar.add_trace(
                go.Scatterpolar(
                    r=[row[c] for c in categories],
                    theta=["Capítulos Ingeridos", "Capítulos Totais"],
                    fill="toself",
                    name=row["title"],
                )
            )
        fig_radar.update_layout(
            polar={"radialaxis": {"visible": True}},
            showlegend=True,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # ── Detail table ──
    st.subheader("Detalhes por Novel")
    st.dataframe(
        df[["title", "chapters", "total_chapters_expected"]].rename(
            columns={
                "title": "Novel",
                "chapters": "Capítulos Ingeridos",
                "total_chapters_expected": "Capítulos Totais",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
