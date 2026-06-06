# Murim Knowledge Base

Sistema de extração, processamento e disponibilização de conhecimento estruturado sobre web-novels do gênero *Murim / Wuxia / Xianxia / Cultivation*.

```
Sites de novels  →  Scrapers  →  Capítulos brutos  →  Pipeline NLP
       ↓                                                      ↓
Persistência (PostgreSQL)  ←──  Entidades (personagens, organizações, locais, relacionamentos)
       ↓
API REST (FastAPI)  +  Dashboard (Streamlit)  +  Grafo de conhecimento (NetworkX)
```

## Funcionalidades

- Catalogar personagens, alcunhas, títulos e relacionamentos
- Mapear seitas, clãs, alianças e hierarquias
- Indexar localizações (cidades, montanhas, reinos)
- Busca semântica (sentence-transformers) e lexical
- Visualização de grafo de relacionamentos (NetworkX + Plotly)
- Exportação de dados estruturados

## Instalação

```bash
# Clonar o repositório
git clone https://github.com/animesdoshad/murim-knowledge-base.git
cd murim_knowledge_base

# Criar e ativar virtual environment
python -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Configurar ambiente
cp .env.example .env
# Editar DATABASE_URL para PostgreSQL, ou manter SQLite para desenvolvimento

# Executar migrações
alembic upgrade head
```

## Uso

```bash
# API REST (documentação em http://localhost:8000/docs)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dashboard Streamlit
streamlit run app/dashboard/main.py
```

### Scraping via API

```bash
curl -X POST http://localhost:8000/api/v1/scrape \
  -H "Content-Type: application/json" \
  -d '{"source": "generic", "novel_slug": "meu-romance", "index_url": "https://exemplo.com/romance/"}'
```

## Testes

```bash
pytest tests/
```

## Arquitetura

Clean Architecture com as camadas:

```
app/
├── core/           # Domínio (entidades, interfaces, use cases, unit of work)
├── repositories/   # Adaptadores SQLAlchemy
├── models/         # ORM (11 tabelas)
├── scrapers/       # BaseScraper + GenericScraper
├── processing/     # Pipeline NLP (6 módulos)
├── api/            # FastAPI (32 rotas)
├── dashboard/      # Streamlit (4 páginas)
└── utils/          # Config + logging
```

### Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x + Alembic |
| Banco | PostgreSQL / SQLite |
| Scraping | requests + BeautifulSoup4 |
| NLP | spaCy + sentence-transformers |
| Dashboard | Streamlit + Plotly + NetworkX |

## Documentação

Documentação detalhada do universo Murim disponível em `docs/`:

| Diretório | Conteúdo |
|---|---|
| `docs/reference/` | Documentos de referência técnica e guias |
| `docs/worldbuilding/` | Material de worldbuilding (seitas, clãs, hierarquias, mapas) |
| `docs/source_material/` | Fontes originais (novels, capítulos, artigos) |

Consulte `PROJECT_STATUS.md` para o estado atual do desenvolvimento.

## Licença

Projeto para uso pessoal e educacional.