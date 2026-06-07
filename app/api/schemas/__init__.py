"""
Pydantic schemas (request/response DTOs) for the public API.

The schemas are intentionally decoupled from the domain entities so the
wire format can evolve independently of the persistence model.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------


class ORMBase(BaseModel):
    """Base config: allow building from ORM attributes."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class PageMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    total: int
    limit: int
    offset: int


class Page(BaseModel):
    """Generic paginated wrapper: ``{items, meta}``."""

    items: list[Any]
    meta: PageMeta


# ---------------------------------------------------------------------------
# Alias / Title
# ---------------------------------------------------------------------------


class AliasRead(ORMBase):
    alias_type: str
    alias_value: str


class AliasCreate(BaseModel):
    alias_type: str = Field(..., min_length=1, max_length=100)
    alias_value: str = Field(..., min_length=1, max_length=255)


class TitleRead(ORMBase):
    title: str


class TitleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------


class CharacterRead(ORMBase):
    id: str
    name: str
    canonical_name: str
    gender: str | None = None
    description: str | None = None
    first_appearance: str | None = None
    appearance_frequency: int = 0
    aliases: list[AliasRead] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    relationships: dict[str, list[str]] = Field(default_factory=dict)
    has_embedding: bool = False


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    canonical_name: str | None = None
    gender: str | None = None
    description: str | None = None
    first_appearance: str | None = None


class CharacterUpdate(BaseModel):
    name: str | None = None
    gender: str | None = None
    description: str | None = None
    first_appearance: str | None = None


class CharacterRelationshipCreate(BaseModel):
    related_character_id: str
    relationship_type: str = Field(..., min_length=1, max_length=100)


class CharacterLocationLink(BaseModel):
    location_id: str = Field(..., min_length=36, max_length=36)


class CharacterOrganizationLink(BaseModel):
    organization_id: str = Field(..., min_length=36, max_length=36)
    role: str | None = Field(None, max_length=100)


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------


class ChapterRead(ORMBase):
    id: str
    novel_id: str
    chapter_number: int
    title: str | None = None
    word_count: int = 0
    snippet: str | None = None


class ChapterDetail(ChapterRead):
    content: str


class ChapterCreate(BaseModel):
    chapter_number: int = Field(..., ge=0)
    title: str | None = None
    content: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Novel
# ---------------------------------------------------------------------------


class NovelRead(ORMBase):
    id: str
    title: str
    author: str | None = None
    genre: str | None = None
    description: str | None = None
    source_url: str | None = None
    language: str = "en"
    total_chapters: int = 0


class NovelCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str | None = None
    genre: str | None = None
    description: str | None = None
    source_url: str | None = None
    language: str = "en"


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


class OrganizationRead(ORMBase):
    id: str
    name: str
    type: str
    description: str | None = None
    parent_org_id: str | None = None
    headquarters_id: str | None = None
    subsidiary_ids: list[str] = Field(default_factory=list)
    member_ids: list[str] = Field(default_factory=list)
    rival_ids: list[str] = Field(default_factory=list)
    ally_ids: list[str] = Field(default_factory=list)


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    parent_org_id: str | None = None
    headquarters_id: str | None = None


class OrganizationRelationshipCreate(BaseModel):
    related_organization_id: str
    relationship_type: str = Field(..., pattern="^(rival|ally|subordinate|parent)$")


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------


class LocationRead(ORMBase):
    id: str
    name: str
    type: str
    description: str | None = None
    region: str | None = None
    realm: str | None = None
    parent_location_id: str | None = None
    sub_location_ids: list[str] = Field(default_factory=list)
    character_ids: list[str] = Field(default_factory=list)
    organization_ids: list[str] = Field(default_factory=list)


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    region: str | None = None
    realm: str | None = None
    parent_location_id: str | None = None


# ---------------------------------------------------------------------------
# Search & graph
# ---------------------------------------------------------------------------


class SearchHit(BaseModel):
    id: str
    name: str
    kind: str  # "character" | "organization" | "location" | "novel"
    score: float = 1.0
    snippet: str | None = None


class SearchResponse(BaseModel):
    query: str
    total: int
    hits: list[SearchHit]


class GraphNode(BaseModel):
    id: str
    kind: str
    label: str
    attrs: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str
    attrs: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str = "0.1.0"
    time: datetime


# ---------------------------------------------------------------------------
# Scrape
# ---------------------------------------------------------------------------


class ScrapeRequest(BaseModel):
    source: str = "generic"
    novel_slug: str = Field(..., min_length=1, max_length=255)
    index_url: str | None = None
    base_url: str | None = None
    domain: str | None = None
    reverse_chapter_list: bool = True
    resume: bool = True


class ScrapeChapterItem(BaseModel):
    chapter_number: int
    title: str | None = None
    db_chapter_id: str | None = None
    skipped: bool = False


class ScrapeResponse(BaseModel):
    novel_slug: str
    novel_title: str | None = None
    novel_id: str | None = None
    total: int
    chapters: list[ScrapeChapterItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
