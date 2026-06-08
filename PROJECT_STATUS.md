# PROJECT_STATUS — Murim Knowledge Base

> Documento vivo que reflete o estado real do workspace.
> Última atualização: 2026-06-07 (sessão 22 — Alias Detector)

---

## 1. Visão Geral

**Murim Knowledge Base** é um sistema completo de extração, processamento e disponibilização de conhecimento estruturado sobre web-novels do gênero *Murim / Wuxia / Xianxia / Cultivation*.

Pipeline conceitual:

```
Sites de novels  →  Scrapers  →  Capítulos brutos  →  Pipeline NLP
       ↓                                                      ↓
 Persistência (PostgreSQL)  ←──  Entidades (personagens, organizações, locais, relacionamentos)
       ↓
 API REST (FastAPI)  +  Dashboard (Streamlit)  +  Grafo de conhecimento (NetworkX)
```

O sistema permite:
- Catalogar personagens, suas alcunhas, títulos e relacionamentos
- Mapear seitas, clãs, alianças e suas hierarquias
- Indexar localizações (cidades, montanhas, reinos)
- Oferecer busca semântica (sentence-transformers) e lexical
- Visualizar grafo de relacionamentos
- Exportar dados estruturados

---

## 2. Arquitetura

### Clean Architecture dentro de `app/`

```
app/
├── core/                  # Domínio (regras de negócio puras)
│   ├── entities/          # Dataclasses: Character, Novel, Chapter, Location, Organization, CharacterArchetype
│   ├── interfaces/        # Contratos: IRepository, ICharacterRepository, IChapterRepository, INovelRepository, ILocationRepository, IOrganizationRepository
│   ├── use_cases/         # 7 use cases implementados
│   └── unit_of_work.py    # UnitOfWork (context manager)
├── repositories/          # Adapters SQLAlchemy (5 implementados)
├── models/                # ORM (11 tabelas) + Base + Engine
├── scrapers/              # BaseScraper + GenericScraper + registry
├── processing/            # 8 módulos NLP (patterns, ner, title/loc/org detectors, rel extractor, archetype classifier, alias detector)
├── api/                   # HTTP layer
│   ├── routes/            # 6 routers (35 rotas)
│   ├── schemas/           # Pydantic DTOs (28+ schemas)
│   └── dependencies/      # get_uow + encoder lazy
├── dashboard/             # Streamlit (4 páginas implementadas)
└── utils/                 # Config + logging
```

### Suporte de infraestrutura

```
alembic/                  # Migration (1 versão, 11 tabelas)
data/{raw,processed,exports,progress}/
logs/                     # Logs rotativos (10MB, 5 backups)
tests/                    # 5 suítes + conftest.py (68 testes, pytest puro)
```

### Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Web Framework / API | FastAPI + Uvicorn |
| ORM / Migrations | SQLAlchemy 2.x + Alembic |
| Banco de Dados | PostgreSQL (psycopg2) — SQLite in-memory para testes |
| Scraping | requests + BeautifulSoup4 + lxml + tenacity |
| NLP | spaCy (en_core_web_lg) + sentence-transformers (fallback regex) |
| Dashboard | Streamlit + Plotly + NetworkX |
| Data Science | pandas + numpy + scikit-learn + rapidfuzz |
| Config | pydantic-settings + python-dotenv |
| Testes | TestClient (httpx) + pytest + pytest-asyncio |

---

## 3. Estrutura de Diretórios

```
murim_knowledge_base/
├── .env.example
├── .venv/                       # Virtual environment (Python 3.12)
├── PROJECT_STATUS.md            # Este arquivo
├── README.md                    # Instalação, uso, arquitetura, docs
├── docs/
│   ├── reference/                # Documentos de referência técnica
│   ├── worldbuilding/            # Material de worldbuilding
│   └── source_material/          # Fontes originais
├── requirements.txt
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py      # Migration completa (11 tabelas)
├── app/
│   ├── __init__.py
│   ├── main.py                  # Factory FastAPI + lifespan + CORS + /health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── character.py     # Character, Alias, Relationship
│   │   │   ├── archetype.py     # CharacterArchetype, NarrativeRole, CombatStyle, PersonalityTrait
│   │   │   ├── location.py      # Location
│   │   │   ├── novel.py         # Novel, Chapter
│   │   │   └── organization.py  # Organization, OrganizationRelationship
│   │   ├── interfaces/
│   │   │   ├── __init__.py
│   │   │   ├── repository.py            # IRepository[T] genérico
│   │   │   ├── character_repository.py  # ICharacterRepository
│   │   │   ├── chapter_repository.py    # IChapterRepository
│   │   │   ├── location_repository.py   # ILocationRepository
│   │   │   ├── novel_repository.py      # INovelRepository
│   │   │   └── organization_repository.py # IOrganizationRepository
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   ├── build_knowledge_graph.py    # NetworkX graph builder
│   │   │   ├── classify_character_archetype.py  # Archetype classification
│   │   │   ├── deduplicate_characters.py   # rapidfuzz dedup
│   │   │   ├── extract_entities.py         # NLP pipeline controller
│   │   │   ├── generate_embeddings.py      # Embedding generation
│   │   │   ├── ingest_chapter.py           # Scraper → DB
│   │   │   └── ingest_entities.py          # Extract → Dedup → DB
│   │   └── unit_of_work.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── character_repository.py
│   │   ├── chapter_repository.py
│   │   ├── location_repository.py
│   │   ├── novel_repository.py
│   │   └── organization_repository.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py              # Engine, SessionLocal, Base, get_db
│   │   ├── character.py         # Character, Alias, Title, Relationship + assoc tables
│   │   ├── location.py          # Location
│   │   ├── novel.py             # Novel, Chapter
│   │   └── organization.py      # Organization, OrganizationRelationship
│   ├── scrapers/
│   │   ├── __init__.py          # Registry / factory
│   │   ├── base.py              # BaseScraper (retry, rate-limit, progress)
│   │   └── generic.py           # GenericScraper configurável
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── patterns.py          # Catálogo de títulos, orgs, locais, relacionamentos
│   │   ├── ner.py               # NER (spaCy + regex fallback)
│   │   ├── title_detector.py    # Detector de títulos honoríficos
│   │   ├── location_detector.py # Detector de locais
│   │   ├── organization_detector.py # Detector de organizações
│   │   └── relationship_extractor.py # Extrator de relacionamentos
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas/__init__.py  # 28+ Pydantic schemas
│   │   ├── dependencies/__init__.py  # get_uow + encoder lazy
│   │   └── routes/
│   │       ├── __init__.py      # api_router agregador
│   │       ├── novels.py        # /novels + /novels/{id}/chapters (6 rotas)
│   │       ├── characters.py    # /characters + aliases/titles/relationships/archetypes (11 rotas)
│   │       ├── organizations.py # /organizations + rivals/allies (6 rotas)
│   │       ├── locations.py     # /locations + sub-locations (4 rotas)
│   │       ├── search.py        # /search (lexical + semantic) (1 rota)
│   │       └── graph.py         # /graph (NetworkX → JSON) (1 rota)
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point Streamlit (st.navigation)
│   │   ├── api_client.py        # Cliente HTTP / ASGI interno
│   │   └── pages/
│   │       ├── __init__.py
│   │       ├── overview.py      # Visão Geral (KPIs, gráficos, inserção rápida)
│   │       ├── characters.py    # Personagens (listagem, filtro)
│   │       ├── graph.py         # Grafo interativo (Plotly + NetworkX)
│   │       └── search.py        # Busca lexical/semântica
│   └── utils/
│       ├── __init__.py
│       ├── config.py            # AppConfig (pydantic-settings) + singleton
│       └── logging_config.py    # Logging console + RotatingFileHandler
├── data/
│   ├── __init__.py
│   ├── raw/                     # Vazio
│   ├── processed/               # Vazio
│   ├── exports/                 # Vazio
│   └── progress/                # Progresso de scrapers (JSON)
├── logs/                        # Logs rotativos
└── tests/
    ├── __init__.py
    ├── conftest.py              # Fixtures compartilhadas (sqlite_session_factory, sqlite_uow, sample_chapter, api_client)
    ├── test_pipeline.py         # 5 testes (persistência + scraper)
    ├── test_nlp.py              # 12 testes (NLP pipeline)
    ├── test_api.py              # 17 testes (API REST)
    └── test_archetype.py        # 16 testes (archetype classification)
```

---

## 4. Funcionalidades Implementadas

| # | Funcionalidade | Local | Status |
|---|---|---|---|
| 1 | Clean Architecture completa | `app/core/`, `app/repositories/`, `app/models/` | ✅ Completo |
| 2 | Config via env vars (pydantic-settings) | `app/utils/config.py` | ✅ Completo |
| 3 | Logging estruturado com rotação | `app/utils/logging_config.py` | ✅ Completo |
| 4 | Engine adaptativo (Postgres ou SQLite) | `app/models/base.py` | ✅ Completo |
| 5 | 11 modelos ORM + 2 M2M association tables | `app/models/` | ✅ Completo |
| 6 | Migration Alembic cobrindo 11 tabelas | `alembic/versions/0001_initial.py` | ✅ Completo |
| 7 | Scraper base: retry, rate-limit, progresso | `app/scrapers/base.py` | ✅ Completo |
| 8 | GenericScraper configurável | `app/scrapers/generic.py` | ✅ Completo |
| 9 | Registry / factory de scrapers | `app/scrapers/__init__.py` | ✅ Completo |
| 10 | 6 entidades de domínio + canonical keys | `app/core/entities/` | ✅ Completo |
| 11 | 6 interfaces de repositório | `app/core/interfaces/` | ✅ Completo |
| 12 | UnitOfWork context manager | `app/core/unit_of_work.py` | ✅ Completo |
| 13 | 5 repositórios SQLAlchemy concretos | `app/repositories/` | ✅ Completo |
| 14 | IngestChapterUseCase com idempotência | `app/core/use_cases/ingest_chapter.py` | ✅ Completo |
| 15 | Pipeline NLP completo (7 módulos) | `app/processing/` | ✅ Completo |
| 16 | ExtractEntitiesUseCase (NÃO toca DB) | `app/core/use_cases/extract_entities.py` | ✅ Completo |
| 17 | DeduplicateCharactersUseCase (rapidfuzz) | `app/core/use_cases/deduplicate_characters.py` | ✅ Completo |
| 18 | BuildKnowledgeGraphUseCase (NetworkX) | `app/core/use_cases/build_knowledge_graph.py` | ✅ Completo |
| 19 | IngestEntitiesUseCase (extract → dedup → DB) | `app/core/use_cases/ingest_entities.py` | ✅ Completo |
| 20 | API REST completa (FastAPI, 35 rotas) | `app/api/` + `app/main.py` | ✅ Completo |
| 21 | `/api/v1/novels` + `/chapters` (CRUD) | `app/api/routes/novels.py` | ✅ Completo |
| 22 | `/api/v1/characters` + alias/title/relationship | `app/api/routes/characters.py` | ✅ Completo |
| 23 | `/api/v1/organizations` + rivals/allies | `app/api/routes/organizations.py` | ✅ Completo |
| 24 | `/api/v1/locations` + sub-locations | `app/api/routes/locations.py` | ✅ Completo |
| 25 | `/api/v1/search` (lexical + embedding) | `app/api/routes/search.py` | ✅ Completo |
| 26 | `/api/v1/graph` (NetworkX → JSON) | `app/api/routes/graph.py` | ✅ Completo |
| 27 | `/api/v1/scrape` (trigger scraper) | `app/api/routes/scrape.py` | ✅ Completo |
| 28 | `/health` (liveness probe) | `app/main.py` | ✅ Completo |
| 29 | CORS, OpenAPI metadata, lifespan | `app/main.py` | ✅ Completo |
| 30 | Dependency injection (UoW + encoder lazy) | `app/api/dependencies/__init__.py` | ✅ Completo |
| 31 | Dashboard Streamlit (4 páginas) | `app/dashboard/` | ✅ Implementado |
| 32 | Dashboard: Visão Geral (KPIs, inserção rápida) | `app/dashboard/pages/overview.py` | ✅ Implementado |
| 33 | Dashboard: Personagens (listagem, filtro) | `app/dashboard/pages/characters.py` | ✅ Implementado |
| 34 | Dashboard: Grafo interativo (Plotly + NetworkX) | `app/dashboard/pages/graph.py` | ✅ Implementado |
| 35 | Dashboard: Busca (lexical/semântica) | `app/dashboard/pages/search.py` | ✅ Implementado |
| 36 | Dashboard: API client (in-process + HTTP) | `app/dashboard/api_client.py` | ✅ Implementado |
| 37 | `GenerateEmbeddingsUseCase` (encoder → persist) | `app/core/use_cases/generate_embeddings.py` | ✅ Completo |
| 38 | `POST /characters/{id}/embed` (gera embedding sob demanda) | `app/api/routes/characters.py` | ✅ Completo |
| 39 | `POST /characters/embed-all` (gera embeddings em lote) | `app/api/routes/characters.py` | ✅ Completo |
| 40 | `set_embedding` no `ICharacterRepository` + `CharacterRepository` | `app/core/interfaces/character_repository.py`, `app/repositories/character_repository.py` | ✅ Completo |
| 41 | Embedding pipeline: `_to_orm` e `_to_entity` propagam `Character.embedding` | `app/repositories/character_repository.py` | ✅ Completo |
| 42 | `ICharacterRepository.link_location` / `unlink_location` | `app/core/interfaces/character_repository.py` | ✅ Completo |
| 43 | `ICharacterRepository.link_organization` / `unlink_organization` | `app/core/interfaces/character_repository.py` | ✅ Completo |
| 44 | `CharacterRepository.link_location` / `unlink_location` | `app/repositories/character_repository.py` | ✅ Completo |
| 45 | `CharacterRepository.link_organization` / `unlink_organization` | `app/repositories/character_repository.py` | ✅ Completo |
| 46 | `POST /characters/{id}/locations` — link character → location | `app/api/routes/characters.py` | ✅ Completo |
| 47 | `DELETE /characters/{id}/locations/{location_id}` — unlink character → location | `app/api/routes/characters.py` | ✅ Completo |
| 48 | `POST /characters/{id}/organizations` — link character → organization | `app/api/routes/characters.py` | ✅ Completo |
| 49 | `DELETE /characters/{id}/organizations/{org_id}` — unlink character → organization | `app/api/routes/characters.py` | ✅ Completo |
| 50 | `ICharacterRepository.add_relationship` / `get_relationships` / `remove_relationship` | `app/core/interfaces/character_repository.py` | ✅ Completo |
| 51 | `CharacterRepository.add_relationship` / `get_relationships` / `remove_relationship` | `app/repositories/character_repository.py` | ✅ Completo |
| 52 | `POST /characters/{id}/relationships` — usa repositório (Clean Architecture) | `app/api/routes/characters.py` | ✅ Completo |
| 53 | `IngestEntitiesUseCase._ingest_relationships` — usa repositório (Clean Architecture) | `app/core/use_cases/ingest_entities.py` | ✅ Completo |
| 54 | `ILocationRepository.get_characters` / `IOrganizationRepository.get_members` | `app/core/interfaces/` | ✅ Completo |
| 55 | `LocationRepository.get_characters` / `OrganizationRepository.get_members` | `app/repositories/` | ✅ Completo |
| 56 | BuildKnowledgeGraphUseCase: contagem de locations robusta (explícita) | `app/core/use_cases/build_knowledge_graph.py` | ✅ Completo |
| 57 | 34 testes passando via `pytest tests/` | `tests/` + `tests/conftest.py` | ✅ Completo |
| 58 | `POST /scrape` — trigger scraper via API REST | `app/api/routes/scrape.py` | ✅ Completo |
| 59 | `ScrapeRequest` / `ScrapeResponse` schemas | `app/api/schemas/__init__.py` | ✅ Completo |
| 60 | `Dockerfile` multi-stage build (Python 3.12-slim) | `Dockerfile` | ✅ Completo |
| 61 | `docker-compose.yml` (Postgres + API + Dashboard) | `docker-compose.yml` | ✅ Completo |
| 62 | `.dockerignore` + `.pre-commit-config.yaml` | Raiz | ✅ Completo |
| 63 | `Makefile` (run-api, run-dashboard, test, lint, migrate, docker-*) | `Makefile` | ✅ Completo |
| 64 | `pyproject.toml` (ruff, mypy configs) | `pyproject.toml` | ✅ Completo |
| 65 | CI (GitHub Actions) — lint, typecheck, test com Postgres service | `.github/workflows/ci.yml` | ✅ Completo |
| 66 | `NovelBinScraper` — scraper dedicado para novelbin.com | `app/scrapers/novelbin.py` | ✅ Completo |
| 67 | `NovelUpdatesScraper` — metadata scraper para novelupdates.com | `app/scrapers/novelupdates.py` | ✅ Completo |
| 68 | Scraper registry atualizado (generic, novelbin, novelupdates) | `app/scrapers/__init__.py` | ✅ Completo |
| 69 | `ScrapeRequest` suporta `index_url`, `base_url`, `domain` opcionais | `app/api/schemas/__init__.py`, `app/api/routes/scrape.py` | ✅ Completo |
| 70 | Dashboard: busca por substring funcional em Personagens | `app/dashboard/pages/characters.py` | ✅ Completo |
| 71 | Dashboard: CRUD completo (editar/deletar) via API | `app/dashboard/pages/characters.py` | ✅ Completo |
| 72 | Dashboard: paginação real (page/offset/per-page) | `app/dashboard/pages/characters.py` | ✅ Completo |
| 73 | Dashboard: export CSV em todas as páginas | `app/dashboard/pages/*.py` | ✅ Completo |
| 74 | Dashboard: inserção rápida de Localizações | `app/dashboard/pages/overview.py` | ✅ Completo |
| 75 | Dashboard: dark mode (auto-detect Streamlit theme) | `app/dashboard/main.py`, `app/dashboard/pages/graph.py` | ✅ Completo |
| 76 | Dashboard: filtro por tipo no Grafo | `app/dashboard/pages/graph.py` | ✅ Completo |
| 77 | `CharacterArchetype` domain entity (enums: NarrativeRole, CombatStyle, PersonalityTrait) | `app/core/entities/archetype.py` | ✅ Completo |
| 78 | `ArchetypeClassifier` NLP classifier (keyword-based) | `app/nlp/archetype_classifier.py` | ✅ Completo |
| 79 | `IChapterRepository` interface (get_by_novel, get_chapters_by_character, search_by_content) | `app/core/interfaces/chapter_repository.py` | ✅ Completo |
| 80 | `ChapterRepository` SQLAlchemy implementation | `app/repositories/chapter_repository.py` | ✅ Completo |
| 81 | `ClassifyCharacterArchetype` use case | `app/core/use_cases/classify_character_archetype.py` | ✅ Completo |
| 82 | `ClassifyAllCharacters` batch use case | `app/core/use_cases/classify_character_archetype.py` | ✅ Completo |
| 83 | `POST /characters/{id}/classify` — classify single character | `app/api/routes/characters.py` | ✅ Completo |
| 84 | `GET /characters/{id}/archetype` — get previously classified archetype | `app/api/routes/characters.py` | ✅ Completo |
| 85 | `POST /characters/classify-all` — batch classify all characters | `app/api/routes/characters.py` | ✅ Completo |
| 86 | `ArchetypeResponse` / `ClassifyAllResponse` Pydantic schemas | `app/api/schemas/__init__.py` | ✅ Completo |
| 87 | `set_archetype` on `ICharacterRepository` + `CharacterRepository` | `app/core/interfaces/character_repository.py`, `app/repositories/character_repository.py` | ✅ Completo |
| 88 | `chapters` property on `UnitOfWork` | `app/core/unit_of_work.py` | ✅ Completo |
| 89 | 16 archetype tests (unit + integration + API) | `tests/test_archetype.py` | ✅ Completo |
| 90 | `AliasHit` dataclass + `detect_aliases()` — alias detection from context phrases | `app/processing/alias_detector.py` | ✅ Completo |
| 91 | `aliases` field on `ChapterExtraction` + integrated into `ExtractEntitiesUseCase` | `app/core/use_cases/extract_entities.py` | ✅ Completo |
| 92 | 17 alias detector tests (unit + integration) | `tests/test_alias_detector.py` | ✅ Completo |

---

## 5. Funcionalidades em Desenvolvimento

| # | Funcionalidade | Local | Progresso | Pendência |
|---|---|---|---|---|
| — | Nenhuma no momento | — | — | Todos os itens de alta/média prioridade concluídos |

---

## 6. Backlog

### Pipeline NLP

- [x] `GenerateEmbeddingsUseCase` — persiste vetor no `Character.embedding`
- [x] `POST /characters/{id}/embed` — gera embedding sob demanda
- [x] `POST /characters/embed-all` — gera embeddings em lote
- [x] Detector de aliases a partir de contexto ("also known as", "whose real name was", "formerly known as")
- [ ] Co-referência ("he" → personagem anterior mencionado)
- [ ] Modelo spaCy customizado / fine-tuned para Murim

### Scrapers

- [x] `NovelUpdatesScraper` — metadata scraper para novelupdates.com
- [x] `NovelBinScraper` — scraper dedicado para novelbin.com
- [x] `NovelFireScraper` — scraper dedicado para novelfire.net
- [x] `WuxiaWorldScraper` — scraper dedicado para wuxiaworld.com
- [ ] Suporte a sites em português (opção `language="pt"`)

### Dashboard (UX)

- [x] Refinar página de Personagens com busca por substring funcional
- [x] Adicionar CRUD completo via dashboard (editar/deletar)
- [x] Paginação real nas listagens
- [x] Dark mode (auto-detect do tema Streamlit)
- [x] Exportar dados (CSV, JSON)
- [ ] Testes E2E para o dashboard (Playwright)

### DevOps / Documentação

- [x] `README.md` (instalação, uso, arquitetura)
- [x] `Dockerfile` + `docker-compose.yml` (Postgres + API + dashboard)
- [x] `Makefile` ou `pyproject.toml` com scripts (`run-api`, `run-dashboard`, `scrape`, `migrate`, `test`)
- [x] Pre-commit (ruff, mypy)
- [x] CI (GitHub Actions)
- [x] `conftest.py` + fixtures pytest compartilhadas

---

## 7. Problemas Conhecidos

### Bugs Potenciais

1. ~~**`test_api.py` — `test_graph_serialization`**: O teste cria manualmente associações character↔organization direto no ORM.~~ **CORRIGIDO na sessão 12 — teste agora usa API endpoints.**

2. ~~**`graph.py` — estatísticas de locations**: `BuildKnowledgeGraphUseCase` calcula `locations` como `G.number_of_nodes() - len(characters) - len(orgs) - (1 if novel_id else 0)`, que é frágil.~~ **CORRIGIDO na sessão 12 — contagem agora é explícita via `len(locations)`.**

3. ~~**`IngestEntitiesUseCase._ingest_locations`** — Incrementa `result.new_locations` incondicionalmente.~~ **VERIFICADO na sessão 12 — código já incrementa apenas no branch `else` (location nova).**

4. ~~**`IngestEntitiesUseCase._ingest_organizations`** — Semântica de "novo" vs "atualizado" não trackeada.~~ **VERIFICADO na sessão 12 — contador incrementa apenas no branch `else` (org nova).**

### Inconsistências Arquiteturais

1. ~~**`update_character` (PATCH)**: Acessa ORM diretamente.~~ **CORRIGIDO na sessão 7.**

2. ~~**`add_alias` e `add_title`**: Também acessam ORM diretamente nos routers.~~ **CORRIGIDO na sessão 7.**

3. ~~**`link_characters_to_locations` e `link_characters_to_organizations`**: Não há use cases ou endpoints dedicados.~~ **CORRIGIDO na sessão 9.**

4. ~~**`IngestEntitiesUseCase._ensure_character`**: Cria personagens placeholder sem incrementar contador.~~ **CORRIGIDO na sessão 7.**

5. ~~**`add_relationship` endpoint** — Acessa `RelationshipORM` diretamente.~~ **CORRIGIDO na sessão 7/9 — agora usa `ICharacterRepository.add_relationship`.**

6. ~~**`IngestEntitiesUseCase._ingest_relationships`** — Importa `RelationshipORM` e faz queries diretas.~~ **CORRIGIDO na sessão 7/9 — agora usa `ICharacterRepository.add_relationship`.**

7. ~~**`ICharacterRepository` incompleto** — Faltam métodos de relationship.~~ **CORRIGIDO na sessão 7/9 — interface tem `add_relationship`, `get_relationships`, `remove_relationship`.**

8. ~~**`ILocationRepository` / `IOrganizationRepository` incompletos** — Faltam navegação reversa.~~ **CORRIGIDO — interfaces e implementações têm `get_characters` e `get_members`.**

### Débitos Técnicos

1. ~~**Testes rodam standalone** — `sys.path.insert`, runners manuais.~~ **CORRIGIDO na sessão 8.**

2. ~~**`test_api.py` — pool global** — engine SQLite global.~~ **CORRIGIDO na sessão 8.**

3. ~~**Sem interface gráfica para scraping** — só via código.~~ **CORRIGIDO na sessão 10 — `POST /scrape`.**

4. **Sem versionamento de schema NLP**: Os padrões em `patterns.py` são versionados apenas pelo git. Não há migration para dados NLP quando novos padrões são adicionados.

5. **`Character.embedding` não indexado**: O embedding é armazenado como JSON string em `Text`. Sem índice de similaridade (ex: pgvector), a busca semântica é O(n) por scan linear.

6. ~~**Dashboard UX**: Falta paginação real, CRUD completo (editar/deletar), dark mode, export (CSV/JSON).~~ **CORRIGIDO na sessão 15.**

---

## 8. Próximos Passos Prioritários

### 🟡 Prioridade ALTA (impacto direto no core)

1. ~~**pgvector / pg_trgm para busca semântica eficiente** — Atualmente O(n) scan linear. Com pgvector: HNSW/IVF index → O(log n). Requer PostgreSQL + extensão.~~ **CONCLUÍDO na sessão 18.**

2. **WuxiaWorldScraper** — Fonte majoritária de novels Murim/Wuxia licenciadas. Estrutura DOM diferente, precisa scraper dedicado.

### 🟡 Prioridade MÉDIA (NLP pipeline)

3. ~~**Detector de aliases por contexto** — "also known as", "whose real name was", "formerly known as" → extrai aliases automaticamente.~~ **CONCLUÍDO na sessão 21.**

4. **Co-referência básica** — Resolver pronomes ("he", "she", "the elder") → personagem anterior na mesma cena.

### 🟢 Prioridade BAIXA (UX e qualidade)

5. **Testes E2E Dashboard (Playwright)** — Cobertura de fluxos críticos: login, CRUD, navegação, graph, search.

6. **Suporte a sites em português** — Opção `language="pt"` no GenericScraper + patterns PT-BR.

7. **Modelo spaCy customizado / fine-tuned para Murim** — NER específico para termos de cultivation (dantian, meridian, qi, sect, clan, realm).

8. **Versionamento de schema NLP** — Migration system para `patterns.py` quando novos padrões são adicionados.

---

## 9. Histórico de Progresso

### Sessão 1 (foundation)

- Estrutura de pastas, modelos ORM, Alembic config.
- **Arquivos:** `app/models/`, `alembic/`, `requirements.txt`

### Sessão 2 (domínio + persistência + scraper)

- 4 entidades de domínio, 5 interfaces, 4 repositórios, UnitOfWork, IngestChapterUseCase, GenericScraper, smoke tests.
- **Arquivos:** `app/core/entities/`, `app/core/interfaces/`, `app/core/unit_of_work.py`, `app/core/use_cases/ingest_chapter.py`, `app/repositories/`, `app/scrapers/`, `tests/test_pipeline.py`

### Sessão 3 (NLP pipeline)

- 6 módulos de processamento (patterns, ner, title/loc/org detectors, relationship_extractor)
- 4 use cases novos: ExtractEntitiesUseCase, DeduplicateCharactersUseCase, BuildKnowledgeGraphUseCase, IngestEntitiesUseCase
- 12 testes NLP passando
- **Arquivos:** `app/processing/`, `app/core/use_cases/extract_entities.py`, `app/core/use_cases/deduplicate_characters.py`, `app/core/use_cases/build_knowledge_graph.py`, `app/core/use_cases/ingest_entities.py`, `tests/test_nlp.py`

### Sessão 4 (API REST)

- `app/main.py` — factory FastAPI com CORS, lifespan, OpenAPI customizado, `/health`
- `app/api/schemas/__init__.py` — 25+ schemas Pydantic
- `app/api/dependencies/__init__.py` — get_uow + encoder sentence-transformers (lazy, thread-safe, fail-soft)
- 7 routers (32 rotas no total)
- 7 testes de integração API
- **Corrigido (bugs que quebrariam em Postgres):**
  - OrganizationRepository.get_rivals/get_allies — passavam string em vez de UUID
  - LocationRepository.get_sub_locations — mesmo bug
  - app/models/base.py — rejeitava max_overflow com SQLite
  - get_uow — precisava __enter__ antes de yield
- **Arquivos:** `app/main.py`, `app/api/`, `tests/test_api.py`

### Sessão 5 (Dashboard + Auditoria — esta sessão)

**Adicionado:**
- Dashboard Streamlit funcional com 4 páginas:
  - `main.py` — entry point com st.navigation
  - `api_client.py` — cliente HTTP/ASGI (in-process via TestClient ou remoto via requests)
  - `overview.py` — KPIs, gráfico de pizza, inserção rápida, tabelas recentes
  - `characters.py` — listagem de personagens com filtro
  - `graph.py` — grafo interativo (NetworkX → Plotly)
  - `search.py` — busca lexical/semântica

**Auditado:**
- Inventário completo de 47+ arquivos Python implementados
- Identificados 5 bugs potenciais, 5 débitos técnicos, 4 inconsistências arquiteturais
- Backlog priorizado com 9 itens

**Resultado:** Sistema funcional com API REST (27 rotas), Dashboard (4 páginas), Pipeline NLP, 24 testes passando.

### Sessão 6 (GenerateEmbeddingsUseCase + Embedding endpoints)

**Adicionado:**
- `app/core/use_cases/generate_embeddings.py` — `GenerateEmbeddingsUseCase`:
  - `execute(character_id)` — gera embedding usando sentence-transformers e persiste no `Character.embedding`
  - `execute_all(force=False)` — gera embeddings para todos os personagens sem embedding (ou força regeneração)
- `POST /api/v1/characters/{id}/embed` — endpoint para gerar embedding de um personagem específico
- `POST /api/v1/characters/embed-all?force=true` — endpoint para gerar embeddings em lote
- `set_embedding(character_id, embedding)` — adicionado ao `ICharacterRepository` e implementado em `CharacterRepository`
- `_to_orm` e `_to_entity` agora propagam o campo `Character.embedding`
- 3 novos testes de API para o fluxo de embeddings

**Arquivos modificados:**
- `app/core/interfaces/character_repository.py` — adicionado `set_embedding` no contrato
- `app/repositories/character_repository.py` — implementação + propagação de embedding em `_to_orm`/`_to_entity`
- `app/core/use_cases/__init__.py` — export do novo use case
- `app/api/routes/characters.py` — 2 novos endpoints + import do use case
- `tests/test_api.py` — 3 novos testes

**Arquivos criados:**
- `app/core/use_cases/generate_embeddings.py` — novo use case

**Resultado:** Embeddings funcionais via API. Busca semântica (`/search?semantic=true`) agora funciona com dados reais quando o modelo sentence-transformers está disponível. **27 testes passando** (5 pipeline + 12 NLP + 10 API).

### Sessão 7 (Correção de bugs críticos)

**Corrigido:**
1. **Contador `new_organizations`** (`ingest_entities.py:161`) — Agora verifica `get_by_name_type` antes de upsertar, incrementando apenas quando uma organização é realmente nova.
2. **Paginação de chapters** (`novels.py:93`) — Agora usa `repo.chapters_count(novel_id)` com `COUNT(*)` real no DB em vez de `len(items)`.
3. **Acesso direto ao ORM nos routers** (`characters.py`) — Refatorado:
   - `update_character` (PATCH) → `ICharacterRepository.update()` (via `CharacterRepository.update`)
   - `add_alias` (POST .../aliases) → `ICharacterRepository.add_alias()`
   - `add_title` (POST .../titles) → `ICharacterRepository.add_title()`
   - Todos os métodos agora residem no contrato da interface e na implementação concreta, eliminando dependência direta de ORM na camada API.
4. **`_ensure_character`** (`ingest_entities.py:222`) — Agora recebe `result` como parâmetro e incrementa `result.new_characters` quando um personagem placeholder é criado (antes era silencioso).

**Arquivos modificados:**
- `app/core/use_cases/ingest_entities.py` — `_ingest_organizations` + `_ensure_character`
- `app/core/interfaces/novel_repository.py` — adicionado `chapters_count`
- `app/repositories/novel_repository.py` — implementado `chapters_count`
- `app/api/routes/novels.py` — `list_chapters` usa `chapters_count` real
- `app/core/interfaces/character_repository.py` — adicionado `update`, `add_alias`, `add_title`
- `app/repositories/character_repository.py` — implementados `update`, `add_alias`, `add_title`
- `app/api/routes/characters.py` — routers refatorados para usar os novos métodos do repositório

**Resultado:** 4 bugs corrigidos. Camada API não acessa mais ORM diretamente (PATCH, aliases, titles). Contadores de estatísticas precisos. **27 testes passando**.

### Sessão 8 (Migração para pytest + conftest.py)

**Adicionado:**
- `tests/conftest.py` — 4 fixtures compartilhadas:
  - `sqlite_session_factory` — cria engine SQLite in-memory com `StaticPool` e `sessionmaker`
  - `sqlite_uow` — `UnitOfWork` usando a session factory
  - `sample_chapter` — `NovelChapter` preenchido com conteúdo realístico contendo personagens, organizações e locais famosos de Murim
  - `api_client` — `(TestClient, session_factory)` tuple com engine SQLite e `get_uow` dependency override; limpa o DB entre usos

**Migrado/purificado (3 test files):**
- `tests/test_pipeline.py` — removido `sys.path.insert`, `_build_sqlite_uow`, `if __name__ == "__main__"` runner. Usa `sqlite_uow` e `sqlite_session_factory` fixtures.
- `tests/test_nlp.py` — removido `sys.path.insert`, `SAMPLE_CHAPTER`, `_build_uow`, `if __name__ == "__main__"` runner. Usa `sqlite_session_factory` e `sample_chapter` fixtures.
- `tests/test_api.py` — removido `sys.path.insert`, `os.environ.setdefault`, `_test_engine` global, `_override_get_uow`, `_new_client()`, `if __name__ == "__main__"` runner. Usa `api_client` fixture.

**Arquivos criados:**
- `tests/conftest.py` — fixtures pytest compartilhadas

**Arquivos modificados:**
- `tests/test_pipeline.py` — migrado para pytest
- `tests/test_nlp.py` — migrado para pytest
- `tests/test_api.py` — migrado para pytest

**Resultado:** Os 3 test files agora são pytest puro. `pytest tests/` executa todos os 27 testes. Sem mais `sys.path.insert`, sem mais runners manuais, sem mais engine global. **27 testes passando via `pytest tests/`**.

### Sessão 9 (Character-location e character-organization linking)

**Adicionado:**
- **Entidade**: `locations: List[str]` (IDs de locations) adicionado ao `Character` dataclass (`app/core/entities/character.py`)
- **Interface**: 4 novos métodos no `ICharacterRepository`:
  - `link_location(character_id, location_id) -> bool`
  - `unlink_location(character_id, location_id) -> bool`
  - `link_organization(character_id, organization_id, role=None) -> bool`
  - `unlink_organization(character_id, organization_id) -> bool`
- **Repositório**: Implementação em `CharacterRepository` — usa `relationship.append`/`remove` para gerenciar as M2M association tables `character_locations` e `character_organizations`. `_to_entity` agora popula `Character.locations` a partir do ORM.
- **Schemas**: `CharacterLocationLink` e `CharacterOrganizationLink` Pydantic models (`app/api/schemas/__init__.py`). `CharacterRead` agora inclui `locations`.
- **API**: 4 novos endpoints no `characters.py` (total sobe de 27 → 31 rotas):
  - `POST /characters/{id}/locations` — associa personagem a localização
  - `DELETE /characters/{id}/locations/{location_id}` — remove associação
  - `POST /characters/{id}/organizations` — associa personagem a organização
  - `DELETE /characters/{id}/organizations/{org_id}` — remove associação

**Testes (4 novos):**
- `test_character_location_linking` — link, verify in GET, unlink, verify empty
- `test_character_location_link_404` — link para UUID inexistente → 404
- `test_character_organization_linking` — link, verify in GET, unlink, verify empty
- `test_character_organization_link_404` — link para UUID inexistente → 404

**Arquivos modificados:**
- `app/core/entities/character.py` — adicionado `locations: List[str]`
- `app/core/interfaces/character_repository.py` — 4 novos métodos abstratos
- `app/repositories/character_repository.py` — implementação + `_to_entity` atualizado
- `app/api/schemas/__init__.py` — novos schemas, `CharacterRead.locations`
- `app/api/routes/characters.py` — 4 novos endpoints + import dos schemas
- `tests/test_api.py` — 4 novos testes

**Resultado:** Gap arquitetural preenchido — as M2M association tables (`character_locations`, `character_organizations`) agora são populadas via API. Anteriormente só existiam no schema do banco e no ORM, sem código para preenchê-las. **31 testes passando via `pytest tests/`**.

### Sessão 10 (API endpoint para scraping)

**Adicionado:**
- **Schemas**: `ScrapeRequest` (source, novel_slug, index_url, base_url, reverse_chapter_list, resume) e `ScrapeResponse` (total, chapters, errors, novel_id, novel_title) em `app/api/schemas/__init__.py`
- **Router**: `app/api/routes/scrape.py` com `POST /scrape` — aceita configuração do GenericScraper, executa `scrape_novel()` com `IngestChapterUseCase` acoplado, retorna resumo com capítulos e seus `db_chapter_id`
- **Registro**: Router registrado em `app/api/routes/__init__.py` com prefixo `/scrape`

**Testes (3 novos):**
- `test_scrape_endpoint_unknown_source` — source inválido → 400
- `test_scrape_endpoint_happy_path` — 2 capítulos mockados, verifica `total=2`
- `test_scrape_endpoint_no_chapters` — página sem capítulos, verifica `total=0`

**Arquivos criados:**
- `app/api/routes/scrape.py` — novo router

**Arquivos modificados:**
- `app/api/schemas/__init__.py` — schemas de scrape
- `app/api/routes/__init__.py` — wire do novo router
- `tests/test_api.py` — 3 novos testes

**Resultado:** Scraper agora acionável via `POST /api/v1/scrape`. Total de rotas sobe de 31 para 32. Total de testes sobe de 31 para 34. **34 testes passando via `pytest tests/`**.

### Sessão 11 (Auditoria completa + correção de inconsistências arquiteturais)

**Auditoria:**
- Análise completa de 50+ arquivos Python, configurações, migrações, testes e documentação
- Identificadas 4 novas inconsistências arquiteturais (acesso direto a ORM em router e use case, interfaces de repositório incompletas)
- Identificados 2 novos bugs potenciais (contadores de locations/orgs imprecisos)
- Atualizados débitos técnicos (itens 6-9) e próximos passos prioritários

**Próximos passos definidos (Prioridade ALTA):**
1. Completar `ICharacterRepository` com métodos de relationship character↔character
2. Refatorar `add_relationship` endpoint para usar repositório
3. Refatorar `IngestEntitiesUseCase._ingest_relationships` para usar repositório
4. Corrigir contador `new_locations` em `_ingest_locations`
5. Completar `ILocationRepository` / `IOrganizationRepository` com navegação reversa

**Arquivos modificados:**
- `PROJECT_STATUS.md` — auditoria e backlog atualizados

**Resultado:** Projeto documentado com estado real; roadmap de correções arquiteturais priorizado. **34 testes passando via `pytest tests/`**.

### Sessão 12 (Correção de bugs restantes + auditoria final)

**Corrigido:**
1. **BuildKnowledgeGraphUseCase — contagem de locations frágil** (`app/core/use_cases/build_knowledge_graph.py:143`) — Substituído cálculo por subtração (`G.number_of_nodes() - len(characters) - len(orgs) - ...`) por contagem explícita via `len(locations)` onde `locations = self.uow.locations.list(limit=10_000)`. Elimina fragilidade se novos tipos de node forem adicionados ao grafo.

2. **test_graph_serialization** (`tests/test_api.py:338-358`) — Removida manipulação direta do ORM (`c_orm.organizations.append(o_orm)`). Teste agora usa endpoint `POST /characters/{id}/organizations` via API, respeitando a Clean Architecture.

3. **PROJECT_STATUS.md** — Atualização completa refletindo estado real do código: todas as inconsistências arquiteturais da sessão 11 já estavam corrigidas no código (interfaces completas, repositórios implementados, endpoints usando repositório). Atualizados: tabela de funcionalidades (59 itens), problemas conhecidos (itens corrigidos movidos para histórico), próximos passos (apenas itens reais pendentes).

**Arquivos modificados:**
- `app/core/use_cases/build_knowledge_graph.py` — contagem robusta de locations
- `tests/test_api.py` — teste usa API endpoints
- `PROJECT_STATUS.md` — documentação alinhada ao código real

**Resultado:** Zero inconsistências arquiteturais restantes. Clean Architecture respeitada em toda a codebase. **34 testes passando via `pytest tests/`**.

### Sessão 13 (Documentação + versionamento)

**Adicionado:**
- `README.md` — Documentação completa: descrição do projeto, instalação, uso, scraping via API, testes, arquitetura, stack, e seção de documentação
- `docs/` — Estrutura de documentação organizada:
  - `docs/reference/` — documentos de referência técnica
  - `docs/worldbuilding/` — material de worldbuilding (seitas, clãs, hierarquias)
  - `docs/source_material/` — fontes originais

**Auditoria de documentação:**
- Nenhum arquivo `.docx` encontrado no workspace
- README.md criado (antes ausente)
- Estrutura `docs/` criada para futura organização de documentos de referência
- Estrutura pronta para receber documentos `.docx` ou `.md` de worldbuilding quando disponíveis

**Arquivos criados:**
- `README.md` — documentação do projeto
- `docs/reference/.gitkeep`
- `docs/worldbuilding/.gitkeep`
- `docs/source_material/.gitkeep`

**Arquivos modificados:**
- `PROJECT_STATUS.md` — auditoria de docs registrada, README marcado como concluído no backlog

**Resultado:** Documentação base versionada. Estrutura pronta para receber materiais de worldbuilding. **Commit:** `9dea16b`.

### Sessão 14 (Docker, CI/CD, scrapers dedicados)

**Adicionado:**
- `Dockerfile` — multi-stage build (builder + runtime), Python 3.12-slim, pip install + spaCy model download, HEALTHCHECK, alembic upgrade head automático na inicialização
- `.dockerignore` — exclui `__pycache__`, `.venv`, `.git`, `data/*`, `logs/*`, `.md` (exceto requirements)
- `docker-compose.yml` — 3 serviços: `postgres` (PostgreSQL 16 Alpine com healthcheck), `api` (FastAPI na porta 8000, depende do postgres), `dashboard` (Streamlit na porta 8501)
- `Makefile` — 14 targets: `install`, `run-api`, `run-dashboard`, `migrate`, `downgrade`, `test`, `lint` (ruff), `format` (ruff), `typecheck` (mypy), `docker-build`, `docker-up`, `docker-down`, `clean`, `all`
- `pyproject.toml` — configuração centralizada de ferramentas:
  - `[tool.ruff]` — target py312, line-length 100, lint (E, F, I, N, W, UP, B, C4, SIM), format (double quotes, space indent)
  - `[tool.mypy]` — py312, ignore_missing_imports, check_untyped_defs, warn_return_any, exclui alembic/
- `.pre-commit-config.yaml` — 4 hooks: trailing-whitespace/end-of-file-fixer/check-yaml/check-toml/check-json/check-added-large-files/check-merge-conflict/debug-statements/detect-private-key + ruff (check + format) + mypy
- `.github/workflows/ci.yml` — 3 jobs:
  - `lint` — ruff check + ruff format --check via astral-sh/ruff-action
  - `typecheck` — pip install mypy + dependências, roda `mypy app/`
  - `test` — Postgres service container, pip cache, spacy model download, `pytest tests/ -v --tb=short`
- `NovelBinScraper` (`app/scrapers/novelbin.py`) — scraper dedicado para novelbin.com/novelbin.me:
  - Auto-constrói `index_url` via `https://{domain}/novel-book/{slug}`
  - Selectors pré-configurados para título, autor, descrição, lista de capítulos, conteúdo
  - Compatível com DOM mutation de ambas as variantes de domínio
- `NovelUpdatesScraper` (`app/scrapers/novelupdates.py`) — metadata scraper para novelupdates.com:
  - Extrai título, autor, gêneros, descrição, status, cover_url, rank, rating
  - NÃO suporta `get_chapter_list` / `get_chapter_content` (NU não hospeda capítulos)
  - Ideal para discovery; combinar com NovelBinScraper para conteúdo
- `ScrapeRequest` schema atualizado — `index_url`, `base_url` e `domain` agora são opcionais (scrapers dedicados geram URLs automaticamente)
- Scraper registry atualizado — agora registra `generic`, `novelbin`, `novelupdates`

**Arquivos criados:**
- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `Makefile`
- `pyproject.toml`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml`
- `app/scrapers/novelbin.py`
- `app/scrapers/novelupdates.py`

**Arquivos modificados:**
- `app/scrapers/__init__.py` — registra novos scrapers
- `app/api/schemas/__init__.py` — `ScrapeRequest` com campos opcionais
- `app/api/routes/scrape.py` — kwargs dinâmicos para scrapers dedicados

**Resultado:** Projeto completo com Docker, CI/CD, pre-commit, Makefile, e 3 scrapers (generic, novelbin, novelupdates). **34 testes passando via `pytest tests/`.** **Commit:** `35924da`.

### Sessão 16 (Linting fixes + qualidade de código)

**Corrigido:**
- Erro de sintaxe em `dashboard/api_client.py` (parêntese extra)
- Import faltando `re` em `scrapers/novelupdates.py`
- Imports não utilizados removidos em todo o codebase
- Variáveis ambíguas (`l` → `loc`/`location`) em list comprehensions
- Nomes de variáveis não-convencionais (`G` → `graph`, `COLOR_MAP` → `color_map`)
- `if` aninhados combinados em `dashboard/pages/characters.py`
- Type annotations modernizadas (`Dict/List` → `dict/list`, `Optional[X]` → `X | None`)
- Imports reorganizados e ordenados (isort/ruff)
- Adicionados `# noqa: E402` onde necessário (imports após sys.path)

**Arquivos modificados:** 65 arquivos (maioria formatação/lint via ruff --fix)

**Resultado:** Todos os 34 testes passando. Ruff clean (0 errors). **Commit:** `8914405`.

### Sessão 17 (NovelFire Scraper)

**Adicionado:**
- `app/scrapers/novelfire.py` — scraper dedicado para novelfire.net
  - Configurable CSS selectors com defaults sensatos
  - Extração de metadata: título, autor, gêneros, descrição, cover, status
  - Lista de capítulos com reversão para ordem de leitura
  - Extração de conteúdo com remoção de ruído (scripts, ads, iframes)
  - Resolução de URLs relativas
  - Persistência de progresso via BaseScraper
- Registrado no registry `app/scrapers/__init__.py` como `novelfire`

**Disponível via API:**
```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"source": "novelfire", "novel_slug": "seu-novel-slug"}'
```

**Arquivos criados:** `app/scrapers/novelfire.py`
**Arquivos modificados:** `app/scrapers/__init__.py`

**Resultado:** 4 scrapers disponíveis (generic, novelbin, novelupdates, novelfire). **34 testes passando**. **Commit:** `02e397e`.

### Sessão 18 (pgvector Support para Busca Semântica Eficiente)

**Adicionado:**
- Dependência `pgvector>=0.2.0` em `requirements.txt`
- Nova coluna `embedding_vec` no modelo `Character` — usa pgvector nativo (`Vector(384)`) no PostgreSQL, `Text` no SQLite
- Custom type `EmbeddingVector` (TypeDecorator) — switch automático baseado no dialecto
- Fallback transparente: coluna `embedding` (TEXT/JSON) mantida para compatibilidade
- Migration Alembic `b45450486962` — schema inicial com embedding_vec
- `ICharacterRepository.search_by_embedding()` — interface para busca por similaridade vetorial
- `CharacterRepository.search_by_embedding()` — implementação com:
  - pgvector HNSW index no PostgreSQL (`embedding_vec <=> query_vec`) → O(log n)
  - Fallback in-Python cosine similarity para SQLite → O(n)
- Atualizado `POST /api/v1/search` para usar pgvector quando disponível
- `set_embedding()` popula ambas as colunas automaticamente

**Arquivos criados:** `alembic/versions/b45450486962_initial_schema_with_pgvector_support.py`
**Arquivos modificados:**
- `requirements.txt` — pgvector dependency
- `app/models/character.py` — EmbeddingVector type + embedding_vec column
- `app/repositories/character_repository.py` — search_by_embedding() + dual column population
- `app/core/interfaces/character_repository.py` — search_by_embedding() contract
- `app/api/routes/search.py` — usa pgvector first, fallback to lexical+python cosine

**Resultado:** Busca semântica agora O(log n) com pgvector (vs O(n) scan linear). **34 testes passando**. Ruff clean.

### Sessão 19 (WuxiaWorldScraper + pgvector fix)

**Adicionado:**
- `app/scrapers/wuxiaworld.py` — scraper dedicado para wuxiaworld.com
  - Configurable CSS selectors com defaults para estrutura moderna do WuxiaWorld
  - Extração de metadata: título, autor, gêneros, descrição, cover, status
  - Lista de capítulos com reversão para ordem de leitura
  - Extração de conteúdo com remoção de ruído (scripts, ads, iframes, nav)
  - Resolução de URLs relativas
  - Persistência de progresso via BaseScraper
- Registrado no registry `app/scrapers/__init__.py` como `wuxiaworld`

**Corrigido:**
- pgvector `Vector` type não funcionava com SQLite (testes falhavam)
- Substituído por custom `EmbeddingVector` TypeDecorator — usa pgvector.Vector no PostgreSQL, Text no SQLite
- Migration regenerada (`b45450486962`) — embedding_vec como Text (ORM faz o switch)

**Arquivos criados:** `app/scrapers/wuxiaworld.py`, `alembic/versions/b45450486962_initial_schema_with_pgvector_support.py`
**Arquivos modificados:**
- `app/scrapers/__init__.py` — registra wuxiaworld
- `app/models/character.py` — EmbeddingVector TypeDecorator + embedding_vec column
- `requirements.txt` — pgvector mantido

**Resultado:** 5 scrapers disponíveis (generic, novelbin, novelupdates, novelfire, wuxiaworld). **34 testes passando**. Ruff clean.

### Sessão 20 (Character Archetype Classification System)

**Adicionado:**
- **Entidade**: `CharacterArchetype` dataclass com enums `NarrativeRole`, `CombatStyle`, `PersonalityTrait` (`app/core/entities/archetype.py`)
- **Interface**: `IChapterRepository` — `get_by_novel`, `get_chapters_by_character`, `search_by_content` (`app/core/interfaces/chapter_repository.py`)
- **Interface**: `set_archetype` adicionado ao `ICharacterRepository`
- **Repositório**: `ChapterRepository` — implementação SQLAlchemy de `IChapterRepository` (`app/repositories/chapter_repository.py`)
- **Use Case**: `ClassifyCharacterArchetype` — classifica um personagem usando `ArchetypeClassifier` + `IChapterRepository` para buscar capítulos, persiste via `set_archetype`
- **Use Case**: `ClassifyAllCharacters` — classifica todos os personagens de um novel em batch
- **Classifier**: `ArchetypeClassifier` — NLP keyword-based classifier para archetype (`app/nlp/archetype_classifier.py`)
- **API**: 3 novos endpoints (`app/api/routes/characters.py`):
  - `POST /characters/{id}/classify` — classifica um personagem
  - `GET /characters/{id}/archetype` — retorna archetype previamente classificado
  - `POST /characters/classify-all` — classifica todos os personagens
- **Schemas**: `ArchetypeResponse`, `ClassifyAllResponse` (`app/api/schemas/__init__.py`)
- **Migração**: `c1a2b3c4d5e6_add_archetype_column_to_characters.py` — adiciona coluna `archetype` ao banco
- **Unit of Work**: `chapters` property adicionada ao `UnitOfWork`

**Testes (16 novos):**
- Unit tests: 6 (vazio, dominante, combat style, narrative role, personality trait, low confidence)
- Integration tests: 4 (use case classify, classify all, already classified, not found)
- API tests: 6 (endpoint classify, archetype get, classify-all, not found, no chapters, empty corpus)

**Arquivos criados:**
- `app/core/entities/archetype.py`
- `app/core/interfaces/chapter_repository.py`
- `app/repositories/chapter_repository.py`
- `app/core/use_cases/classify_character_archetype.py`
- `app/nlp/archetype_classifier.py`
- `tests/test_archetype.py`
- `alembic/versions/c1a2b3c4d5e6_add_archetype_column_to_characters.py`

**Arquivos modificados:**
- `app/core/interfaces/__init__.py` — exporta `IChapterRepository`
- `app/core/interfaces/character_repository.py` — adicionado `set_archetype`
- `app/core/entities/__init__.py` — exporta `CharacterArchetype`
- `app/core/unit_of_work.py` — adiciona `ChapterRepository` como `uow.chapters`
- `app/repositories/__init__.py` — exporta `ChapterRepository`
- `app/repositories/character_repository.py` — implementa `set_archetype`
- `app/models/character.py` — corrigido erro de sintaxe
- `app/api/routes/characters.py` — 3 novos endpoints
- `app/api/schemas/__init__.py` — schemas de archetype

**Resultado:** Character archetype classification system completo. 50 testes passando via `pytest tests/`. Ruff clean. **Commit:** `0b6aa67`.

### Sessão 21 (Bug Fixes from Code Review)

**Corrigido:**
- **Bug crítico** `search.py:57`: `.get("_similarity")` em dataclass → `getattr()` — corrige AttributeError em runtime
- **Bug** `character_repository.py:418`: `except Exception: pass` → `except SQLAlchemyError: pass` — erros SQL reais não são mais engolidos silenciosamente
- **Bug de arquitetura** `organizations.py:97-121`: lógica ORM `add_relationship` movida do router para `OrganizationRepository.add_relationship()` — respeita Clean Architecture
- **Interface**: `add_relationship()` adicionado ao `IOrganizationRepository`
- **Migração**: `d2e3f4a5b6c7` — altera `embedding_vec` para `vector(384)` no PostgreSQL (no-op no SQLite)
- **Código morto removido**: import `AliasORM` não utilizado em `chapter_repository.py`, caracteres chineses em `api_client.py`
- **README.md**: contagens atualizadas (5 scrapers, 36 rotas, 9 tabelas, 6 módulos NLP)

**Teste adicionado:**
- `test_search_semantic` — valida o caminho de busca semântica com embeddings

**Resultado:** 51/51 testes passando. **Commit:** `9321b38`.

### Sessão 22 (Alias Detector — Context Phrase Extraction)

**Adicionado:**
- **Módulo**: `AliasHit` dataclass + `detect_aliases()` — detection of character aliases from context phrases in prose (`app/processing/alias_detector.py`)
  - Supports 10+ patterns: "also known as", "whose real name was", "whose true name was", "whose name was", "formerly known as", "once called", "born as", "known as", "called", "named"
  - Confidence scoring per pattern type (0.70–0.95)
  - Deduplication across overlapping patterns
  - Context fragment extraction for each hit
- **Integration**: `aliases: list[AliasHit]` field added to `ChapterExtraction` dataclass
- **Pipeline**: `detect_aliases()` integrated into `ExtractEntitiesUseCase.execute()`
- **Tests (17 new)**: Unit (14) + Integration (3)
  - Empty text, no aliases, known-as, also-known-as, whose-real-name, formerly-known, once-called, born-as, multiple aliases same character, confidence scores, context fragments, canonical names, title prefixes, complex sentences
  - Integration: alias in extracted entities, empty corpus, dominant character

**Arquivos criados:**
- `app/processing/alias_detector.py`
- `tests/test_alias_detector.py`

**Arquivos modificados:**
- `app/core/use_cases/extract_entities.py` — `aliases` field + integration
- `app/processing/__init__.py` — exports AliasHit, detect_aliases

**Resultado:** 68/68 testes passando. Ruff clean. **Commit:** pending.

---

## 10. Como Rodar

```bash
# Ativar venv
source .venv/bin/activate

# Criar .env a partir do template
cp .env.example .env
# Editar DATABASE_URL para apontar ao Postgres, se desejado

# Subir Postgres + rodar migrations (ou usar SQLite editando .env)
alembic upgrade head

# Rodar a API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Documentação: http://localhost:8000/docs

# Rodar o Dashboard
streamlit run app/dashboard/main.py

# Rodar todos os testes
pytest tests/
```
