"""
Visualizacao do Grafo de Conhecimento (NetworkX -> Plotly) com dark mode.
Enhanced with character network, path finding, and graph stats.
"""

from __future__ import annotations

import logging

import plotly.graph_objects as go
import streamlit as st

from app.dashboard.api_client import get

logger = logging.getLogger(__name__)

COLOR_MAP = {
    "character": "#ef553b",
    "organization": "#636efa",
    "location": "#00cc96",
    "novel": "#ab63fa",
}


def _render_plotly_graph(nodes: list[dict], edges: list[dict], title: str) -> None:
    """Render a Plotly graph from nodes and edges."""
    if not nodes:
        st.info("Grafo vazio.")
        return

    try:
        import networkx as nx

        graph = nx.Graph()
        for n in nodes:
            graph.add_node(n["id"], kind=n.get("kind", "unknown"))
        for e in edges:
            graph.add_edge(e["source"], e["target"])
        pos = nx.spring_layout(graph, seed=42, k=2 / (max(1, len(nodes)) ** 0.5))
    except Exception as exc:
        logger.warning("Failed to generate layout: %s", exc)
        st.warning("Erro ao gerar layout.")
        return

    if not pos:
        st.info("Grafo vazio após filtro.")
        return

    bg_color = "#0e1117" if st.get_option("theme.base") == "dark" else "white"
    font_color = "#fafafa" if bg_color == "#0e1117" else "#262730"

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for n in nodes:
        nid = n["id"]
        x, y = pos.get(nid, (0, 0))
        node_x.append(x)
        node_y.append(y)
        node_text.append(n.get("name") or n.get("label", nid))
        node_color.append(COLOR_MAP.get(n.get("kind", ""), "#999999"))
        degree = sum(1 for e in edges if e["source"] == nid or e["target"] == nid)
        node_size.append(12 + 6 * degree)

    edge_traces = []
    for e in edges:
        src, tgt = e["source"], e["target"]
        if src in pos and tgt in pos:
            x0, y0 = pos[src]
            x1, y1 = pos[tgt]
            label = e.get("relation") or e.get("label", "")
            edge_traces.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode="lines",
                    line={"color": "#888888", "width": 1},
                    hoverinfo="text" if label else "skip",
                    hovertext=label,
                    showlegend=False,
                )
            )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        marker={"color": node_color, "size": node_size, "line": {"width": 1, "color": font_color}},
        textfont={"size": 10, "color": font_color},
    )

    layout = go.Layout(
        title={"text": title, "font": {"color": font_color}},
        showlegend=False,
        hovermode="closest",
        margin={"b": 0, "l": 0, "r": 0, "t": 40},
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
    )

    fig = go.Figure(data=edge_traces + [node_trace], layout=layout)
    st.plotly_chart(fig, use_container_width=True)


def _tab_full_graph() -> None:
    """Full knowledge graph tab."""
    try:
        graph_data = get("api/v1/graph")
        nodes = graph_data["nodes"]
        edges = graph_data["edges"]
        stats = graph_data["stats"]
    except Exception as exc:
        logger.warning("Failed to load graph data: %s", exc)
        st.error("Erro ao carregar o grafo.")
        return

    if not nodes:
        st.info("O grafo está vazio. Ingeste capítulos para visualizar.")
        return

    st.write(
        f"Nós: {stats['nodes']} | Arestas: {stats['edges']} | "
        f"Characters: {stats.get('characters', 0)} | "
        f"Organizations: {stats.get('organizations', 0)} | "
        f"Locations: {stats.get('locations', 0)}"
    )

    kinds = list({n["kind"] for n in nodes})
    selected_kinds = st.multiselect("Filtrar por tipo", kinds, default=kinds, key="graph_filter")

    filtered_nodes = [n for n in nodes if n["kind"] in selected_kinds]
    filtered_ids = {n["id"] for n in filtered_nodes}
    filtered_edges = [
        e for e in edges if e["source"] in filtered_ids and e["target"] in filtered_ids
    ]

    _render_plotly_graph(filtered_nodes, filtered_edges, "Grafo de Conhecimento")

    st.markdown("### Legenda")
    cols = st.columns(len(COLOR_MAP))
    for idx, (kind, color) in enumerate(COLOR_MAP.items()):
        with cols[idx]:
            st.markdown(
                f"<span style='color:{color};font-size:18px'>●</span> {kind}",
                unsafe_allow_html=True,
            )


def _tab_character_network() -> None:
    """Character network extraction tab."""
    col_id, col_depth = st.columns([3, 1])
    with col_id:
        character_id = st.text_input(
            "ID do personagem",
            key="network_char_id",
            placeholder="UUID do personagem",
        )
    with col_depth:
        depth = st.slider("Profundidade", 1, 5, 2, key="network_depth")

    if not character_id:
        st.info("Insira o UUID de um personagem para ver sua rede.")
        return

    with st.spinner("Carregando rede do personagem..."):
        try:
            result = get(
                f"api/v1/graph/character/{character_id}",
                params={"depth": depth},
            )
        except Exception as exc:
            logger.warning("Character network failed: %s", exc)
            st.error("Erro ao carregar rede. Verifique o ID.")
            return

    center_name = result.get("center_character_name", "Unknown")
    st.subheader(f"Rede de: **{center_name}**")
    st.caption(f"Nós: {result.get('node_count', 0)} | Arestas: {result.get('edge_count', 0)}")

    nodes = result.get("nodes", [])
    edges = result.get("edges", [])

    if not nodes:
        st.warning("Nenhum nó na rede.")
        return

    _render_plotly_graph(nodes, edges, f"Rede de {center_name}")


def _tab_path_finding() -> None:
    """Shortest path finding tab."""
    col_src, col_tgt = st.columns(2)
    with col_src:
        source_id = st.text_input(
            "ID origem",
            key="path_source",
            placeholder="UUID do personagem origem",
        )
    with col_tgt:
        target_id = st.text_input(
            "ID destino",
            key="path_target",
            placeholder="UUID do personagem destino",
        )

    if not source_id or not target_id:
        st.info("Insira os UUIDs de origem e destino.")
        return

    with st.spinner("Calculando caminho mais curto..."):
        try:
            result = get(
                "api/v1/graph/path",
                params={"source_id": source_id, "target_id": target_id},
            )
        except Exception as exc:
            logger.warning("Path finding failed: %s", exc)
            st.error("Erro ao calcular caminho.")
            return

    path_length = result.get("path_length", 0)
    source_name = result.get("source_name", "Unknown")
    target_name = result.get("target_name", "Unknown")

    if path_length == 0:
        if source_id == target_id:
            st.info(f"Origem e destino são o mesmo: **{source_name}**")
        else:
            st.warning(f"Sem caminho entre **{source_name}** e **{target_name}**")
        return

    st.success(f"Caminho encontrado: **{path_length}** passos")
    st.caption(f"De **{source_name}** para **{target_name}**")

    path = result.get("path", [])
    if path:
        path_names = [p.get("name") or p.get("id", "?") for p in path]
        st.markdown(" → ".join(f"**{n}**" for n in path_names))

    # Build graph from path
    nodes = [
        {"id": p.get("id", ""), "name": p.get("name") or p.get("id", ""), "kind": "character"}
        for p in path
    ]
    edges = [{"source": path[i]["id"], "target": path[i + 1]["id"]} for i in range(len(path) - 1)]
    _render_plotly_graph(nodes, edges, f"Caminho: {source_name} → {target_name}")


def _tab_graph_stats() -> None:
    """Graph statistics tab."""
    with st.spinner("Carregando estatísticas..."):
        try:
            stats = get("api/v1/graph/stats")
        except Exception as exc:
            logger.warning("Graph stats failed: %s", exc)
            st.error("Erro ao carregar estatísticas.")
            return

    st.subheader("Estatísticas do Grafo")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Nós", stats.get("total_nodes", 0))
    with col2:
        st.metric("Total de Arestas", stats.get("total_edges", 0))
    with col3:
        st.metric("Densidade", f"{stats.get('density', 0):.4f}")

    st.markdown("### Por Tipo")
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Personagens", stats.get("characters", 0))
    with col5:
        st.metric("Organizações", stats.get("organizations", 0))
    with col6:
        st.metric("Locais", stats.get("locations", 0))

    rel_counts = stats.get("relationships", {})
    if rel_counts:
        st.markdown("### Tipos de Relacionamento")
        st.bar_chart(rel_counts)


def show() -> None:
    st.title("Grafo de Conhecimento")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🌐 Grafo Completo", "👤 Rede", "🛤️ Caminho", "📊 Estatísticas"]
    )

    with tab1:
        _tab_full_graph()
    with tab2:
        _tab_character_network()
    with tab3:
        _tab_path_finding()
    with tab4:
        _tab_graph_stats()
