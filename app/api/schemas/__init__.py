"""
Pydantic schemas (request/response DTOs) for the public API.

The schemas are intentionally decoupled from the domain entities so the
wire format can evolve independently of the persistence model.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

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

    items: List[Any]
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
    gender: Optional[str] = None
    description: Optional[str] = None
    first_appearance: Optional[str] = None
    appearance_frequency: int = 0
    aliases: List[AliasRead] = Field(default_factory=list)
    titles: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    relationships: Dict[str, List[str]] = Field(default_factory=dict)
    has_embedding: bool = False


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    canonical_name: Optional[str] = None
    gender: Optional[str] = None
    description: Optional[str] = None
    first_appearance: Optional[str] = None


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    description: Optional[str] = None
    first_appearance: Optional[str] = None


class CharacterRelationshipCreate(BaseModel):
    related_character_id: str
    relationship_type: str = Field(..., min_length=1, max_length=100)


class CharacterLocationLink(BaseModel):
    location_id: str = Field(..., min_length=36, max_length=36)


class CharacterOrganizationLink(BaseModel):
    organization_id: str = Field(..., min_length=36, max_length=36)
    role: Optional[str] = Field(None, max_length=100)


# ---------------------------------------------------------------------------
# Chapter
# ---------------------------------------------------------------------------


class ChapterRead(ORMBase):
    id: str
    novel_id: str
    chapter_number: int
    title: Optional[str] = None
    word_count: int = 0
    snippet: Optional[str] = None


class ChapterDetail(ChapterRead):
    content: str


class ChapterCreate(BaseModel):
    chapter_number: int = Field(..., ge=0)
    title: Optional[str] = None
    content: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Novel
# ---------------------------------------------------------------------------


class NovelRead(ORMBase):
    id: str
    title: str
    author: Optional[str] = None
    genre: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    language: str = "en"
    total_chapters: int = 0


class NovelCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: Optional[str] = None
    genre: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    language: str = "en"


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


class OrganizationRead(ORMBase):
    id: str
    name: str
    type: str
    description: Optional[str] = None
    parent_org_id: Optional[str] = None
    headquarters_id: Optional[str] = None
    subsidiary_ids: List[str] = Field(default_factory=list)
    member_ids: List[str] = Field(default_factory=list)
    rival_ids: List[str] = Field(default_factory=list)
    ally_ids: List[str] = Field(default_factory=list)


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    parent_org_id: Optional[str] = None
    headquarters_id: Optional[str] = None


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
    description: Optional[str] = None
    region: Optional[str] = None
    realm: Optional[str] = None
    parent_location_id: Optional[str] = None
    sub_location_ids: List[str] = Field(default_factory=list)
    character_ids: List[str] = Field(default_factory=list)
    organization_ids: List[str] = Field(default_factory=list)


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    region: Optional[str] = None
    realm: Optional[str] = None
    parent_location_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Search & graph
# ---------------------------------------------------------------------------


class SearchHit(BaseModel):
    id: str
    name: str
    kind: str  # "character" | "organization" | "location" | "novel"
    score: float = 1.0
    snippet: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    total: int
    hits: List[SearchHit]


class GraphNode(BaseModel):
    id: str
    kind: str
    label: str
    attrs: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str
    attrs: Dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: Dict[str, int] = Field(default_factory=dict)


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
    index_url: str = Field(..., min_length=1)
    base_url: str = Field(..., min_length=1)
    reverse_chapter_list: bool = True
    resume: bool = True


class ScrapeChapterItem(BaseModel):
    chapter_number: int
    title: Optional[str] = None
    db_chapter_id: Optional[str] = None
    skipped: bool = False


class ScrapeResponse(BaseModel):
    novel_slug: str
    novel_title: Optional[str] = None
    novel_id: Optional[str] = None
    total: int
    chapters: List[ScrapeChapterItem] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
