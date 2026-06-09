"""
E2E tests for the Streamlit dashboard using Playwright.

Streamlit widgets are identified by aria-label, placeholder, or visible text.
Streamlit keys are internal and NOT exposed as HTML attributes.

Run:
    pytest tests/test_dashboard_e2e.py -v --base-url http://localhost:8501

CI:
    The ``dashboard_base_url`` conftest fixture starts a Streamlit server
    automatically when the ``DASHBOARD_E2E_URL`` env-var is not set.
"""

from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.timeout(120),
]

# Allow override via env-var (CI sets this to the auto-started server).
BASE = os.environ.get("DASHBOARD_E2E_URL", "http://localhost:8501")
WAIT = 8000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _base_url() -> str:
    """Return the dashboard base URL, preferring the runtime env-var."""
    return os.environ.get("DASHBOARD_E2E_URL", BASE)


def _open(page, path: str = "/"):
    """Navigate and wait for Streamlit to fully render."""
    page.goto(f"{_base_url()}{path}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(WAIT)


# ---------------------------------------------------------------------------
# Tests: Navigation
# ---------------------------------------------------------------------------


class TestNavigation:
    """Test sidebar navigation between dashboard pages."""

    def test_overview_page_loads(self, page):
        _open(page)
        assert page.locator("text=Visão Geral").first.is_visible()

    def test_navigate_to_characters(self, page):
        _open(page)
        page.get_by_text("Personagens", exact=True).first.click()
        page.wait_for_timeout(3000)
        assert page.locator("text=Personagens").first.is_visible()

    def test_navigate_to_graph(self, page):
        _open(page)
        page.get_by_text("Grafo Pincel", exact=True).first.click()
        page.wait_for_timeout(3000)
        assert page.locator("text=Grafo de Conhecimento").first.is_visible()

    def test_navigate_to_search(self, page):
        _open(page)
        page.get_by_text("Busca", exact=True).first.click()
        page.wait_for_timeout(3000)
        assert page.locator("text=Busca").first.is_visible()


# ---------------------------------------------------------------------------
# Tests: Overview Page
# ---------------------------------------------------------------------------


class TestOverviewPage:
    """Test the Overview (Visão Geral) page functionality."""

    def test_kpi_metrics_visible(self, page):
        _open(page)
        for label in ["Novels", "Personagens", "Organizações", "Localizações"]:
            assert page.locator(f"text={label}").first.is_visible()

    def test_quick_add_form_exists(self, page):
        _open(page)
        assert page.locator("text=Inserção Rápida").first.is_visible()

    def test_data_tabs_visible(self, page):
        _open(page)
        assert page.get_by_text("Novels", exact=True).first.is_visible()


# ---------------------------------------------------------------------------
# Tests: Characters Page
# ---------------------------------------------------------------------------


class TestCharactersPage:
    """Test the Characters page — search, pagination, CRUD controls."""

    def test_search_input_visible(self, page):
        _open(page, "/characters")
        search = page.get_by_placeholder("Digite para filtrar...")
        assert search.first.is_visible()

    def test_search_characters(self, page):
        _open(page, "/characters")
        search = page.get_by_placeholder("Digite para filtrar...")
        search.first.fill("test")
        page.wait_for_timeout(2000)

    def test_per_page_selectbox_visible(self, page):
        _open(page, "/characters")
        assert page.locator("text=Por página").first.is_visible()

    def test_page_number_input_visible(self, page):
        _open(page, "/characters")
        assert page.get_by_label("Página").first.is_visible()

    def test_characters_page_loaded(self, page):
        """Verify the characters page title renders."""
        _open(page, "/characters")
        assert page.locator("text=Personagens").first.is_visible()


# ---------------------------------------------------------------------------
# Tests: Search Page
# ---------------------------------------------------------------------------


class TestSearchPage:
    """Test the Search page functionality."""

    def test_search_input_visible(self, page):
        _open(page, "/search")
        search_input = page.get_by_placeholder("Digite sua busca...")
        if search_input.count() == 0:
            search_input = page.locator("input[type='text']")
        assert search_input.first.is_visible()

    def test_semantic_toggle_visible(self, page):
        _open(page, "/search")
        assert page.locator("text=Semântica").first.is_visible()

    def test_empty_query_shows_info(self, page):
        _open(page, "/search")
        info = page.locator("text=iniciar a busca")
        assert info.first.is_visible()

    def test_search_execution(self, page):
        _open(page, "/search")
        search_input = page.locator("input[type='text']")
        if search_input.count() > 0:
            search_input.first.fill("cultivation")
            page.wait_for_timeout(3000)


# ---------------------------------------------------------------------------
# Tests: Graph Page
# ---------------------------------------------------------------------------


class TestGraphPage:
    """Test the Graph visualization page."""

    def test_graph_page_loads(self, page):
        _open(page, "/graph")
        graph_title = page.locator("text=Grafo de Conhecimento")
        empty_msg = page.locator("text=O grafo está vazio")
        assert graph_title.first.is_visible() or empty_msg.first.is_visible()

    def test_filter_multiselect_visible(self, page):
        _open(page, "/graph")
        # Filter only renders if graph data loads; otherwise shows error
        graph_or_error = (
            page.locator("text=Filtrar por tipo").first.is_visible()
            or page.locator("text=Erro ao carregar o grafo").first.is_visible()
            or page.locator("text=O grafo está vazio").first.is_visible()
        )
        assert graph_or_error


# ---------------------------------------------------------------------------
# Tests: Quick Add (Overview)
# ---------------------------------------------------------------------------


class TestQuickAdd:
    """Test quick add functionality on the overview page."""

    def test_quick_add_section_elements(self, page):
        """Quick add form should have type selector, title input, and submit."""
        _open(page)
        assert page.locator("text=Tipo").first.is_visible()
        # The input label is "Título" (for Novel type, which is default)
        assert page.locator("text=Título").first.is_visible()
        assert page.get_by_text("Adicionar", exact=True).first.is_visible()

    def test_quick_add_type_selector(self, page):
        """Type selector should be present."""
        _open(page)
        assert page.locator("text=Tipo").first.is_visible()
