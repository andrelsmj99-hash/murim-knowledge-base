"""
Routers package — exposes URL prefixes grouped by aggregate.

All routers accept a :class:`UnitOfWork` and follow the same conventions:
* `GET    /<resource>`            list (paginated)
* `GET    /<resource>/{id}`       retrieve
* `POST   /<resource>`            create
* `PATCH  /<resource>/{id}`       update
* `DELETE /<resource>/{id}`       delete

Search and graph have bespoke shapes.
"""
from fastapi import APIRouter

from . import characters, graph, locations, novels, organizations, scrape, search

api_router = APIRouter()
api_router.include_router(novels.router, prefix="/novels", tags=["novels"])
api_router.include_router(characters.router, prefix="/characters", tags=["characters"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(scrape.router, prefix="/scrape", tags=["scrape"])
