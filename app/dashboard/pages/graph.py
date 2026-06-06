"""
Visualizacao do Grafo de Conhecimento (NetworkX -> Plotly).
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from app.dashboard.api_client import get


def show() -> None:
    st.title("Grafo de Conhecimento")

    try:
        graph_data = get("api/v1/graph")
        nodes = graph_data["nodes"]
        edges = graph_data["edges"]
        stats = graph_data["stats"]
    except Exception:
        st.error("Erro ao carregar o grafo.")
        return

    if not nodes:
        st.info("O grafo esta vazio. Ingeste capitulos para visualizar.")
        return

    st.subheader("Estatisticas")
    st.write(
        f"Nos: {stats['nodes']} | Arestas: {stats['edges']} | "
        f"Characters: {stats.get('characters', 0)} | "
        f"Organizations: {stats.get('organizations', 0)}"
    )

    try:
        import networkx as nx
        G = nx.Graph()
        for n in nodes:
            G.add_node(n["id"], kind=n["kind"])
        for e in edges:
            G.add_edge(e["source"], e["target"])
        pos = nx.spring_layout(G, seed=42, k=2 / (len(nodes) ** 0.5))
    except Exception:
        st.warning("Erro ao gerar layout via NetworkX.")
        return

    if not pos:
        st.info("Grafo vazio.")
        return

    COLOR_MAP = {
        "character": "#ef553b",
        "organization": "#636efa",
        "location": "#00cc96",
        "novel": "#ab63fa",
    }

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for n in nodes:
        nid = n["id"]
        x, y = pos.get(nid, (0, 0))
        node_x.append(x)
        node_y.append(y)
        node_text.append(n.get("label", nid))
        node_color.append(COLOR_MAP.get(n["kind"], "#999999"))
        node_size.append(10 + 5 * len([e for e in edges if e["source"] == nid or e["target"] == nid]))

    edge_traces = []
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in pos and tgt in pos:
            x0, y0 = pos[src]
            x1, y1 = pos[tgt]
            edge_traces.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode="lines",
                    line=dict(color="#888888", width=1),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        marker=dict(color=node_color, size=node_size, line=dict(width=1, color="black")),
        textfont=dict(size=10),
    )

    layout = go.Layout(
        title=dict(text="Grafo"),
        showlegend=False,
        hovermode="closest",
        margin=dict(b=0, l=0, r=0, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
    )

    fig = go.Figure(data=edge_traces + [node_trace], layout=layout)
    st.plotly_chart(fig, use_container_width=True, key="knowledge_graph")

    st.markdown("### Legenda")
    for kind, color in COLOR_MAP.items():
        st.markdown(f"<span style='color:{color}'>●</span> {kind.title()}", unsafe_allow_html=True)
