"""
SQLAlchemy implementation of :class:`ICharacterRepository`.

Maps between the ORM model in :mod:`app.models.character` and the
domain entity in :mod:`app.core.entities.character`.
"""

from __future__ import annotations

import builtins
import json
import logging
import math
import uuid as uuid_module

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.entities import Alias as EntityAlias
from app.core.entities import Character
from app.core.interfaces import ICharacterRepository
from app.models.character import Alias
from app.models.character import Character as CharacterORM

logger = logging.getLogger(__name__)


def _to_uuid(value: str) -> uuid_module.UUID:
    """Convert a string id (from the domain entity) to a ``uuid.UUID`` for the ORM."""
    return uuid_module.UUID(str(value))


def _to_entity(orm: CharacterORM) -> Character:
    """ORM → domain entity."""
    from app.core.entities import CharacterArchetype

    aliases = [
        EntityAlias(
            alias_type=a.alias_type, value=a.alias_value, canonical_value=a.alias_value.lower()
        )
        for a in orm.aliases
    ]
    titles = [t.title for t in orm.titles]
    org_ids = [str(o.id) for o in orm.organizations]
    loc_ids = [str(loc.id) for loc in orm.locations]
    relationships: dict[str, list[str]] = {}
    for rel in orm.relationships:
        relationships.setdefault(rel.relationship_type, []).append(str(rel.related_character_id))

    # Prefer pgvector column if available, fallback to JSON text
    embedding = orm.embedding
    if hasattr(orm, "embedding_vec") and orm.embedding_vec:
        try:
            import json

            embedding = (
                json.loads(orm.embedding_vec)
                if isinstance(orm.embedding_vec, str)
                else orm.embedding_vec
            )
        except Exception:
            logger.debug("Failed to parse embedding_vec for character %s", orm.id, exc_info=True)

    # Handle archetype field if it exists
    archetype = None
    if hasattr(orm, "archetype") and orm.archetype:
        try:
            import json

            archetype_data = (
                json.loads(orm.archetype) if isinstance(orm.archetype, str) else orm.archetype
            )
            if archetype_data:
                archetype = CharacterArchetype(**archetype_data)
        except Exception:
            logger.debug("Failed to parse archetype for character %s", orm.id, exc_info=True)

    return Character(
        id=str(orm.id),
        name=orm.name,
        canonical_name=orm.canonical_name,
        aliases=aliases,
        titles=titles,
        gender=orm.gender,
        first_appearance=orm.first_appearance,
        appearance_frequency=orm.appearance_frequency or 0,
        organizations=org_ids,
        locations=loc_ids,
        relationships=relationships,
        embedding=embedding,
        archetype=archetype,
    )


def _to_orm(entity: Character) -> CharacterORM:
    """Domain entity → ORM (attached to the session, not yet persisted)."""
    import json

    embedding_json = json.dumps(entity.embedding) if entity.embedding else None
    archetype_json = None
    if entity.archetype:
        archetype_json = json.dumps(entity.archetype.__dict__)

    orm = CharacterORM(
        id=_to_uuid(entity.id),
        name=entity.name,
        canonical_name=entity.canonical_name,
        gender=entity.gender,
        first_appearance=entity.first_appearance,
        appearance_frequency=entity.appearance_frequency,
        embedding=embedding_json,
        embedding_vec=embedding_json,  # Also populate pgvector column
        archetype=archetype_json,  # Handle archetype field
    )
    for alias in entity.aliases:
        orm.aliases.append(
            Alias(
                alias_type=alias.alias_type,
                alias_value=alias.value,
            )
        )
    return orm


def _canonical_name(name: str) -> str:
    """Normalization for dedup (lowercase, collapsed whitespace)."""
    return " ".join(name.lower().split())


class CharacterRepository(ICharacterRepository):
    entity_cls = Character

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    # --- read -----------------------------------------------------------

    def get(self, entity_id: str) -> Character | None:
        orm = self.session.get(CharacterORM, _to_uuid(entity_id))
        return _to_entity(orm) if orm else None

    def list(self, *, limit: int = 100, offset: int = 0) -> builtins.list[Character]:
        stmt = select(CharacterORM).order_by(CharacterORM.name).limit(limit).offset(offset)
        return [_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    def count(self) -> int:
        from sqlalchemy import func

        return int(self.session.scalar(select(func.count(CharacterORM.id))) or 0)

    def get_by_canonical_name(self, canonical_name: str) -> Character | None:
        key = _canonical_name(canonical_name)
        stmt = select(CharacterORM).where(CharacterORM.canonical_name == key)
        orm = self.session.execute(stmt).scalar_one_or_none()
        return _to_entity(orm) if orm else None

    def get_by_alias(self, alias_value: str) -> Character | None:
        stmt = (
            select(CharacterORM)
            .join(Alias, Alias.character_id == CharacterORM.id)
            .where(Alias.alias_value == alias_value)
            .limit(1)
        )
        orm = self.session.execute(stmt).scalar_one_or_none()
        return _to_entity(orm) if orm else None

    def search_by_name(self, query: str, *, limit: int = 20) -> builtins.list[Character]:
        if not query:
            return []
        pattern = f"%{query.lower()}%"
        stmt = (
            select(CharacterORM)
            .where(
                or_(
                    CharacterORM.name.ilike(pattern),
                    CharacterORM.canonical_name.ilike(pattern),
                )
            )
            .order_by(CharacterORM.name)
            .limit(limit)
        )
        return [_to_entity(c) for c in self.session.execute(stmt).scalars().all()]

    # --- write ----------------------------------------------------------

    def add(self, entity: Character) -> Character:
        orm = _to_orm(entity)
        self.session.add(orm)
        self.session.flush()
        return _to_entity(orm)

    def delete(self, entity_id: str) -> bool:
        orm = self.session.get(CharacterORM, _to_uuid(entity_id))
        if orm is None:
            return False
        self.session.delete(orm)
        self.session.flush()
        return True

    def upsert_by_canonical_name(self, character: Character) -> Character:
        character.canonical_name = character.canonical_name or _canonical_name(character.name)
        existing = self.get_by_canonical_name(character.canonical_name)
        if existing:
            return existing
        return self.add(character)

    def update(
        self,
        character_id: str,
        *,
        name: str | None = None,
        gender: str | None = None,
        description: str | None = None,
        first_appearance: str | None = None,
    ) -> Character | None:
        orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if orm is None:
            return None
        if name is not None:
            orm.name = name
        if gender is not None:
            orm.gender = gender
        if description is not None:
            orm.description = description
        if first_appearance is not None:
            orm.first_appearance = first_appearance
        self.session.flush()
        return _to_entity(orm)

    def add_alias(self, character_id: str, alias_type: str, alias_value: str) -> bool:
        orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if orm is None:
            return False
        # Check for existing alias to make ingestion idempotent
        existing = [a for a in orm.aliases if a.alias_value == alias_value]
        if existing:
            return False
        orm.aliases.append(Alias(alias_type=alias_type, alias_value=alias_value))
        self.session.flush()
        return True

    def add_title(self, character_id: str, title: str) -> bool:
        from app.models.character import Title as TitleORM

        orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if orm is None:
            return False
        orm.titles.append(TitleORM(character_id=orm.id, title=title))
        self.session.flush()
        return True

    def set_embedding(self, character_id: str, embedding: str) -> None:
        orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if orm is not None:
            orm.embedding = embedding
            orm.embedding_vec = embedding
            self.session.flush()

    def set_archetype(self, character_id: str, archetype) -> bool:
        """
        Set the archetype for a character.

        Args:
            character_id: The ID of the character
            archetype: The CharacterArchetype object to set

        Returns:
            True if successful, False if character not found
        """
        orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if orm is None:
            return False
        try:
            archetype_json = json.dumps(archetype.__dict__) if archetype else None
            orm.archetype = archetype_json
            self.session.flush()
            return True
        except Exception:
            logger.warning(
                "Failed to persist archetype for character %s", character_id, exc_info=True
            )
            return False

    def link_location(self, character_id: str, location_id: str) -> bool:
        from app.models.location import Location as LocationORM

        c_orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if c_orm is None:
            return False
        l_orm = self.session.get(LocationORM, _to_uuid(location_id))
        if l_orm is None:
            return False
        if l_orm not in c_orm.locations:
            c_orm.locations.append(l_orm)
            self.session.flush()
        return True

    def unlink_location(self, character_id: str, location_id: str) -> bool:
        from app.models.location import Location as LocationORM

        c_orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if c_orm is None:
            return False
        l_orm = self.session.get(LocationORM, _to_uuid(location_id))
        if l_orm is None or l_orm not in c_orm.locations:
            return False
        c_orm.locations.remove(l_orm)
        self.session.flush()
        return True

    def link_organization(
        self, character_id: str, organization_id: str, role: str | None = None
    ) -> bool:
        from app.models.organization import Organization as OrganizationORM

        c_orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if c_orm is None:
            return False
        o_orm = self.session.get(OrganizationORM, _to_uuid(organization_id))
        if o_orm is None:
            return False
        if o_orm not in c_orm.organizations:
            c_orm.organizations.append(o_orm)
            self.session.flush()
        return True

    def unlink_organization(self, character_id: str, organization_id: str) -> bool:
        from app.models.organization import Organization as OrganizationORM

        c_orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if c_orm is None:
            return False
        o_orm = self.session.get(OrganizationORM, _to_uuid(organization_id))
        if o_orm is None or o_orm not in c_orm.organizations:
            return False
        c_orm.organizations.remove(o_orm)
        self.session.flush()
        return True

    def add_relationship(
        self, character_id: str, related_character_id: str, relationship_type: str
    ) -> bool:
        from app.models.character import Relationship as RelationshipORM

        c_orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if c_orm is None:
            return False
        target_orm = self.session.get(CharacterORM, _to_uuid(related_character_id))
        if target_orm is None:
            return False
        if character_id == related_character_id:
            return False
        existing = (
            self.session.query(RelationshipORM)
            .filter_by(
                character_id=_to_uuid(character_id),
                related_character_id=_to_uuid(related_character_id),
                relationship_type=relationship_type,
            )
            .first()
        )
        if existing is not None:
            return False
        self.session.add(
            RelationshipORM(
                character_id=_to_uuid(character_id),
                related_character_id=_to_uuid(related_character_id),
                relationship_type=relationship_type,
            )
        )
        self.session.flush()
        return True

    def get_relationships(self, character_id: str) -> dict[str, builtins.list[str]]:
        c_orm = self.session.get(CharacterORM, _to_uuid(character_id))
        if c_orm is None:
            return {}
        result: dict[str, list[str]] = {}
        for rel in c_orm.relationships:
            result.setdefault(rel.relationship_type, []).append(str(rel.related_character_id))
        return result

    def remove_relationship(
        self, character_id: str, related_character_id: str, relationship_type: str
    ) -> bool:
        from app.models.character import Relationship as RelationshipORM

        rel = (
            self.session.query(RelationshipORM)
            .filter_by(
                character_id=_to_uuid(character_id),
                related_character_id=_to_uuid(related_character_id),
                relationship_type=relationship_type,
            )
            .first()
        )
        if rel is None:
            return False
        self.session.delete(rel)
        self.session.flush()
        return True

    def search_by_embedding(
        self, query_vec: list[float], *, limit: int = 20
    ) -> builtins.list[Character]:
        """
        Search characters by vector similarity using pgvector (PostgreSQL).
        Falls back to in-Python cosine similarity if pgvector not available.
        """
        import json

        # Try pgvector first (PostgreSQL with pgvector extension)
        try:
            from sqlalchemy import text

            # Convert query vector to PostgreSQL array format
            vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

            # Use cosine similarity via pgvector (<=> operator)
            stmt = text("""
                SELECT id, name, canonical_name, gender, first_appearance,
                       appearance_frequency, embedding, embedding_vec,
                       1 - (embedding_vec <=> :vec) as similarity
                FROM characters
                WHERE embedding_vec IS NOT NULL
                ORDER BY embedding_vec <=> :vec
                LIMIT :limit
            """)
            result = self.session.execute(stmt, {"vec": vec_str, "limit": limit})
            rows = result.mappings().all()

            if rows:
                characters = []
                for row in rows:
                    # Build character entity from row
                    c = Character(
                        id=str(row["id"]),
                        name=row["name"],
                        canonical_name=row["canonical_name"],
                        gender=row["gender"],
                        first_appearance=row["first_appearance"],
                        appearance_frequency=row["appearance_frequency"] or 0,
                        embedding=row["embedding"],
                        _similarity=float(row["similarity"]),
                    )
                    characters.append(c)
                return characters
        except SQLAlchemyError:
            # pgvector not available or query failed, fall through to Python fallback
            logger.debug("pgvector query failed, falling back to in-Python cosine similarity")

        # Fallback: in-Python cosine similarity (for SQLite or if pgvector unavailable)
        all_chars = self.list(limit=10000)  # Get all characters with embeddings
        scored = []
        for c in all_chars:
            if c.embedding:
                try:
                    emb = json.loads(c.embedding) if isinstance(c.embedding, str) else c.embedding
                    if emb and len(emb) == len(query_vec):
                        dot = sum(x * y for x, y in zip(emb, query_vec, strict=True))
                        na = math.sqrt(sum(x * x for x in emb))
                        nb = math.sqrt(sum(y * y for y in query_vec))
                        if na and nb:
                            sim = dot / (na * nb)
                            c._similarity = sim
                            scored.append(c)
                except Exception:
                    logger.debug(
                        "Skipping character %s in cosine fallback: bad embedding data",
                        c.id,
                        exc_info=True,
                    )

        scored.sort(key=lambda x: getattr(x, "_similarity", 0.0), reverse=True)
        return scored[:limit]


# Re-export the JSON helper so callers can store the embedding column.
def dump_embedding(vector: list[float]) -> str:
    return json.dumps(vector)


def load_embedding(blob: str | None) -> list[float] | None:
    if not blob:
        return None
    return json.loads(blob)
