# PROJECT_STATUS — Murim Knowledge Base

> Documento vivo que reflete o estado real do workspace.
> Última atualização: 2026-06-06 (sessão 10 — API endpoint para scraping + 34 testes)

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
│   ├── entities/          # Dataclasses: Character, Novel, Chapter, Location, Organization
│   ├── interfaces/        # Contratos: IRepository, ICharacterRepository, INovelRepository, ILocationRepository, IOrganizationRepository
│   ├── use_cases/         # 5 use cases implementados
│   └── unit_of_work.py    # UnitOfWork (context manager)
├── repositories/          # Adapters SQLAlchemy (4 implementados)
├── models/                # ORM (11 tabelas) + Base + Engine
├── scrapers/              # BaseScraper + GenericScraper + registry
├── processing/            # 6 módulos NLP (patterns, ner, title/loc/org detectors, rel extractor)
├── api/                   # HTTP layer
│   ├── routes/            # 6 routers (27 rotas)
│   ├── schemas/           # Pydantic DTOs (25+ schemas)
│   └── dependencies/      # get_uow + encoder lazy
├── dashboard/             # Streamlit (4 páginas implementadas)
└── utils/                 # Config + logging
```

### Suporte de infraestrutura

```
alembic/                  # Migration (1 versão, 11 tabelas)
data/{raw,processed,exports,progress}/
logs/                     # Logs rotativos (10MB, 5 backups)
tests/                    # 3 suítes + conftest.py (34 testes, pytest puro)
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
├── README.md                    # AUSENTE
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
│   │   │   ├── location.py      # Location
│   │   │   ├── novel.py         # Novel, Chapter
│   │   │   └── organization.py  # Organization, OrganizationRelationship
│   │   ├── interfaces/
│   │   │   ├── __init__.py
│   │   │   ├── repository.py            # IRepository[T] genérico
│   │   │   ├── character_repository.py  # ICharacterRepository
│   │   │   ├── location_repository.py   # ILocationRepository
│   │   │   ├── novel_repository.py      # INovelRepository
│   │   │   └── organization_repository.py # IOrganizationRepository
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   ├── build_knowledge_graph.py    # NetworkX graph builder
│   │   │   ├── deduplicate_characters.py   # rapidfuzz dedup
│   │   │   ├── extract_entities.py         # NLP pipeline controller
│   │   │   ├── ingest_chapter.py           # Scraper → DB
│   │   │   └── ingest_entities.py          # Extract → Dedup → DB
│   │   └── unit_of_work.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── character_repository.py
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
│   │   ├── schemas/__init__.py  # 25+ Pydantic schemas
│   │   ├── dependencies/__init__.py  # get_uow + encoder lazy
│   │   └── routes/
│   │       ├── __init__.py      # api_router agregador
│   │       ├── novels.py        # /novels + /novels/{id}/chapters (6 rotas)
│   │       ├── characters.py    # /characters + aliases/titles/relationships (8 rotas)
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
    └── test_api.py              # 10 testes (API REST)
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
| 10 | 5 entidades de domínio + canonical keys | `app/core/entities/` | ✅ Completo |
| 11 | 5 interfaces de repositório | `app/core/interfaces/` | ✅ Completo |
| 12 | UnitOfWork context manager | `app/core/unit_of_work.py` | ✅ Completo |
| 13 | 4 repositórios SQLAlchemy concretos | `app/repositories/` | ✅ Completo |
| 14 | IngestChapterUseCase com idempotência | `app/core/use_cases/ingest_chapter.py` | ✅ Completo |
| 15 | Pipeline NLP completo (6 módulos) | `app/processing/` | ✅ Completo |
| 16 | ExtractEntitiesUseCase (NÃO toca DB) | `app/core/use_cases/extract_entities.py` | ✅ Completo |
| 17 | DeduplicateCharactersUseCase (rapidfuzz) | `app/core/use_cases/deduplicate_characters.py` | ✅ Completo |
| 18 | BuildKnowledgeGraphUseCase (NetworkX) | `app/core/use_cases/build_knowledge_graph.py` | ✅ Completo |
| 19 | IngestEntitiesUseCase (extract → dedup → DB) | `app/core/use_cases/ingest_entities.py` | ✅ Completo |
| 20 | API REST completa (FastAPI, 27 rotas) | `app/api/` + `app/main.py` | ✅ Completo |
| 21 | `/api/v1/novels` + `/chapters` (CRUD) | `app/api/routes/novels.py` | ✅ Completo |
| 22 | `/api/v1/characters` + alias/title/relationship | `app/api/routes/characters.py` | ✅ Completo |
| 23 | `/api/v1/organizations` + rivals/allies | `app/api/routes/organizations.py` | ✅ Completo |
| 24 | `/api/v1/locations` + sub-locations | `app/api/routes/locations.py` | ✅ Completo |
| 25 | `/api/v1/search` (lexical + embedding) | `app/api/routes/search.py` | ✅ Completo |
| 26 | `/api/v1/graph` (NetworkX → JSON) | `app/api/routes/graph.py` | ✅ Completo |
| 27 | `/health` (liveness probe) | `app/main.py` | ✅ Completo |
| 28 | CORS, OpenAPI metadata, lifespan | `app/main.py` | ✅ Completo |
| 29 | Dependency injection (UoW + encoder lazy) | `app/api/dependencies/__init__.py` | ✅ Completo |
| 30 | Dashboard Streamlit (4 páginas) | `app/dashboard/` | ✅ Implementado |
| 31 | Dashboard: Visão Geral (KPIs, inserção rápida) | `app/dashboard/pages/overview.py` | ✅ Implementado |
| 32 | Dashboard: Personagens (listagem, filtro) | `app/dashboard/pages/characters.py` | ✅ Implementado |
| 33 | Dashboard: Grafo interativo (Plotly + NetworkX) | `app/dashboard/pages/graph.py` | ✅ Implementado |
| 34 | Dashboard: Busca (lexical/semântica) | `app/dashboard/pages/search.py` | ✅ Implementado |
| 35 | Dashboard: API client (in-process + HTTP) | `app/dashboard/api_client.py` | ✅ Implementado |
| 36 | `GenerateEmbeddingsUseCase` (encoder → persist) | `app/core/use_cases/generate_embeddings.py` | ✅ Completo |
| 37 | `POST /characters/{id}/embed` (gera embedding sob demanda) | `app/api/routes/characters.py` | ✅ Completo |
| 38 | `POST /characters/embed-all` (gera embeddings em lote) | `app/api/routes/characters.py` | ✅ Completo |
| 39 | `set_embedding` no `ICharacterRepository` + `CharacterRepository` | `app/core/interfaces/character_repository.py`, `app/repositories/character_repository.py` | ✅ Completo |
| 40 | Embedding pipeline: `_to_orm` e `_to_entity` propagam `Character.embedding` | `app/repositories/character_repository.py` | ✅ Completo |
| 41 | 27 testes passando via `pytest tests/` | `tests/` + `tests/conftest.py` | ✅ Completo |
| 42 | `ICharacterRepository.link_location` / `unlink_location` | `app/core/interfaces/character_repository.py` | ✅ Completo |
| 43 | `ICharacterRepository.link_organization` / `unlink_organization` | `app/core/interfaces/character_repository.py` | ✅ Completo |
| 44 | `CharacterRepository.link_location` / `unlink_location` | `app/repositories/character_repository.py` | ✅ Completo |
| 45 | `CharacterRepository.link_organization` / `unlink_organization` | `app/repositories/character_repository.py` | ✅ Completo |
| 46 | `POST /characters/{id}/locations` — link character → location | `app/api/routes/characters.py` | ✅ Completo |
| 47 | `DELETE /characters/{id}/locations/{location_id}` — unlink character → location | `app/api/routes/characters.py` | ✅ Completo |
| 48 | `POST /characters/{id}/organizations` — link character → organization | `app/api/routes/characters.py` | ✅ Completo |
| 49 | `DELETE /characters/{id}/organizations/{org_id}` — unlink character → organization | `app/api/routes/characters.py` | ✅ Completo |
| 50 | 31 testes passando via `pytest tests/` (27 + 4 novos) | `tests/test_api.py` | ✅ Completo |
| 51 | `POST /scrape` — trigger scraper via API REST | `app/api/routes/scrape.py` | ✅ Completo |
| 52 | `ScrapeRequest` / `ScrapeResponse` schemas | `app/api/schemas/__init__.py` | ✅ Completo |
| 53 | 34 testes passando via `pytest tests/` (27 + 4 linking + 3 scrape) | `tests/test_api.py` | ✅ Completo |

---

## 5. Funcionalidades em Desenvolvimento

| # | Funcionalidade | Local | Progresso | Pendência |
|---|---|---|---|---|---|
| 1 | Dashboard Streamlit | `app/dashboard/` | 90% | Falta refinar visualizações, adicionar paginação real, melhorar responsividade |
| 2 | Scraper endpoint via API | `app/api/routes/scrape.py` | 100% | `POST /scrape` aceita source, novel_slug, index_url, base_url; retorna capítulos raspados com IDs do DB |

---

## 6. Backlog

### Pipeline NLP

- [x] `GenerateEmbeddingsUseCase` — persiste vetor no `Character.embedding`
- [x] `POST /characters/{id}/embed` — gera embedding sob demanda
- [x] `POST /characters/embed-all` — gera embeddings em lote
- [ ] Detector de aliases a partir de contexto ("also known as", "whose real name was", "formerly known as")
- [ ] Co-referência ("he" → personagem anterior mencionado)
- [ ] Modelo spaCy customizado / fine-tuned para Murim

### Scrapers

- [ ] `NovelUpdatesScraper` ou similar — fonte real para validar com dados verdadeiros
- [ ] `WuxiaWorldScraper`
- [ ] Suporte a sites em português (opção `language="pt"`)

### Dashboard (UX)

- [ ] Refinar página de Personagens com busca por substring funcional
- [ ] Adicionar CRUD completo via dashboard (editar/deletar)
- [ ] Paginação real nas listagens
- [ ] Dark mode
- [ ] Exportar dados (CSV, JSON)

### DevOps / Documentação

- [ ] `README.md` (instalação, uso, arquitetura)
- [ ] `Dockerfile` + `docker-compose.yml` (Postgres + API + dashboard)
- [ ] `Makefile` ou `pyproject.toml` com scripts (`run-api`, `run-dashboard`, `scrape`, `migrate`, `test`)
- [ ] Pre-commit (black, ruff, mypy)
- [ ] CI (GitHub Actions)
- [x] `conftest.py` + fixtures pytest compartilhadas

---

## 7. Problemas Conhecidos

### Bugs Potenciais

1. **`test_api.py` — `test_graph_serialization`**: O teste cria manualmente associações character↔organization direto no ORM. Se a lógica de `_ingest_relationships` ou `_ingest_organizations` mudar, este teste pode quebrar silenciosamente.

2. **`graph.py` — estatísticas de locations**: `BuildKnowledgeGraphUseCase` calcula `locations` como `G.number_of_nodes() - len(characters) - len(orgs) - (1 if novel_id else 0)`, que é frágil — qualquer outro tipo de node quebraria o cálculo.

### Inconsistências Arquiteturais

1. ~~**`update_character` (PATCH)**: Acessa ORM diretamente.~~ **CORRIGIDO na sessão 7.**

2. ~~**`add_alias` e `add_title`**: Também acessam ORM diretamente nos routers.~~ **CORRIGIDO na sessão 7.**

3. ~~**`link_characters_to_locations` e `link_characters_to_organizations`**: Não há use cases ou endpoints dedicados para associar personagens a locais/organizações. A associação é feita apenas via SQL direto nos testes.~~ **CORRIGIDO na sessão 9.**

4. ~~**`IngestEntitiesUseCase._ensure_character`**: Cria personagens placeholder sem incrementar contador.~~ **CORRIGIDO na sessão 7.**

### Débitos Técnicos

1. ~~**Testes rodam standalone**: Cada `tests/test_*.py` faz `sys.path.insert(0, ...)` no topo e define `if __name__ == "__main__"` com runner manual. Impede execução via `pytest` puro.~~ **CORRIGIDO na sessão 8 — todos os testes migrados para pytest com fixtures do conftest.py.**

2. ~~**`test_api.py` — pool global**: O engine SQLite com `StaticPool` é criado no módulo global. Entre testes, as tabelas são truncadas via `table.delete()`, o que pode deixar sequences inconsistentes em outros dialects.~~ **CORRIGIDO na sessão 8 — engine e pool gerenciados pelo conftest.py via fixture `api_client`.**

3. ~~**Sem interface gráfica para scraping**: O scraper só é acionável via código (ou eventual CLI), não via API REST ou dashboard.~~ **CORRIGIDO na sessão 10 — `POST /scrape` endpoint disponível.**

4. **Sem versionamento de schema NLP**: Os padrões em `patterns.py` são versionados apenas pelo git. Não há migration para dados NLP quando novos padrões são adicionados.

5. **`Character.embedding` não indexado**: O embedding é armazenado como JSON string em `Text`. Sem índice de相似idade (ex: pgvector), a busca semântica é O(n) por scan linear.

---

## 8. Próximos Passos Prioritários

### 🔴 Prioridade ALTA (correções)

1. ~~**Corrigir bugs conhecidos**: (4 bugs corrigidos na sessão 7)~~
2. ~~**Endpoints de linking character↔location e character↔organization**: (4 endpoints + 4 testes, sessão 9)~~

### 🟡 Prioridade MÉDIA (núcleo funcional)

3. **Scraper dedicado** (NovelUpdatesScraper ou similar) — `POST /scrape` pronto para uso com GenericScraper, falta scraper especializado
4. **Dockerfile** + **docker-compose.yml**

### 🟢 Prioridade BAIXA (UX e qualidade)

5. Refinar Dashboard (CRUD completo, paginação real, dark mode)
6. Pre-commit + CI (GitHub Actions)
7. Suporte a pgvector para busca semântica eficiente
8. Co-referência e detecção de aliases por contexto
9. Detector de aliases a partir de contexto ("also known as", "whose real name was")
10. ~~**Sem interface gráfica para scraping** — acionar scrapers via API REST: `POST /scrape` implementado (sessão 10)~~

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
