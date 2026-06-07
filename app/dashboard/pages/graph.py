"""
Visualizacao do Grafo de Conhecimento (NetworkX -> Plotly) com dark mode.
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
        st.info("O grafo está vazio. Ingeste capítulos para visualizar.")
        return

    col_stats, col_filter = st.columns([2, 1])
    with col_stats:
        st.write(
            f"Nós: {stats['nodes']} | Arestas: {stats['edges']} | "
            f"Characters: {stats.get('characters', 0)} | "
            f"Organizations: {stats.get('organizations', 0)} | "
            f"Locations: {stats.get('locations', 0)}"
        )

    kinds = list({n["kind"] for n in nodes})
    with col_filter:
        selected_kinds = st.multiselect("Filtrar por tipo", kinds, default=kinds, key="graph_filter")

    filtered_nodes = [n for n in nodes if n["kind"] in selected_kinds]
    filtered_ids = {n["id"] for n in filtered_nodes}
    filtered_edges = [e for e in edges if e["source"] in filtered_ids and e["target"] in filtered_ids]

    try:
        import networkx as nx
        graph = nx.Graph()
        for n in filtered_nodes:
            graph.add_node(n["id"], kind=n["kind"])
        for e in filtered_edges:
            graph.add_edge(e["source"], e["target"])
        pos = nx.spring_layout(graph, seed=42, k=2 / (max(1, len(filtered_nodes)) ** 0.5))
    except Exception:
        st.warning("Erro ao gerar layout via NetworkX.")
        return

    if not pos:
        st.info("Grafo vazio após filtro.")
        return

    color_map = {
        "character": "#ef553b",
        "organization": "#636efa",
        "location": "#00cc96",
        "novel": "#ab63fa",
    }

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for n in filtered_nodes:
        nid = n["id"]
        x, y = pos.get(nid, (0, 0))
        node_x.append(x)
        node_y.append(y)
        node_text.append(n.get("label", nid))
        node_color.append(color_map.get(n["kind"], "#999999"))
        degree = sum(1 for e in filtered_edges if e["source"] == nid or e["target"] == nid)
        node_size.append(12 + 6 * degree)

    edge_traces = []
    for e in filtered_edges:
        src, tgt = e["source"], e["target"]
        if src in pos and tgt in pos:
            x0, y0 = pos[src]
            x1, y1 = pos[tgt]
            edge_traces.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode="lines",
                    line={"color": "#888888", "width": 1},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    bg_color = "#0e1117" if st.get_option("theme.base") == "dark" else "white"
    font_color = "#fafafa" if bg_color == "#0e1117" else "#262730"

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        marker={"color": node_color, "size": node_size, "line": {"width": 1, "color": font_color}},
        textfont={"size": 10, "color": font_color},
    )

    layout = go.Layout(
        title={"text": "Grafo de Conhecimento", "font": {"color": font_color}},
        showlegend=False,
        hovermode="closest",
        margin={"b": 0, "l": 0, "r": 0, "t": 40},
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
    )

    fig = go.Figure(data=edge_traces + [node_trace], layout=layout)
    st.plotly_chart(fig, use_container_width=True, key="knowledge_graph")

    st.markdown("### Legenda")
    cols = st.columns(len(color_map))
    for idx, (kind, color) in enumerate(color_map.items()):
        with cols[idx]:
            st.markdown(f"<span style='color:{color};font-size:18px'>●</span> {kind}", unsafe_allow_html=True)
