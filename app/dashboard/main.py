"""
Entry-point for the Murim Knowledge Base dashboard.

Usage::

    streamlit run app/dashboard/main.py

The page is built around a ``st.navigation`` sidebar with four main views:

1. **Visão Geral** — metrics, quick stats and the latest novel entries
2. **Personagens** — filterable table, detail card, relationship preview
3. **Grafo** — interactive visualisation of the knowledge graph
4. **Busca** — free-text query against the API (lexical + semantic)

Notes on architecture:
- Each view is a function imported from ``pages/`` so the file stays small.
- The API client defaults to the in-process FastAPI app (zero latency).
  To point at a remote server set the env var ``API_BASE_URL``.
- ``st.set_page_config`` must be called *before* any other Streamlit command.
"""
from __future__ import annotations

import os
import sys

import streamlit as st

# Resolve project root so we can import `app.*`
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.dashboard import api_client  # noqa: E402
from app.dashboard.pages import characters, graph, overview, search  # noqa: E402

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Murim Knowledge Base",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Murim Knowledge Base — Extração e visualização de conhecimento de web-novels Murim / Wuxia.",
    },
)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    .st-emotion-cache-1jicfl2 {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Configure API client (in-process by default, remote via env var)
api_base = os.getenv("API_BASE_URL")
if api_base:
    api_client.configure(api_base_url=api_base)
else:
    # In-process mode – wrapped with an internal import to avoid circular refs.
    pass  # _get_client() lazily creates TestClient when needed.

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

overview_page = st.Page(overview.show, title="Visão Geral", icon="🏠")
characters_page = st.Page(characters.show, title="Personagens", icon="⚔️")
graph_page = st.Page(graph.show, title="Grafo Pincel", icon="🕸️")
search_page = st.Page(search.show, title="Busca", icon="🔍")

# Run the selected page
pg = st.navigation([overview_page, characters_page, graph_page, search_page])
pg.run()
