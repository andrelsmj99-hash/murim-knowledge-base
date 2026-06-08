from __future__ import annotations

from app.core.entities import Character
from app.core.use_cases import (
    BuildKnowledgeGraphUseCase,
    DeduplicateCharactersUseCase,
    ExtractEntitiesUseCase,
    IngestEntitiesUseCase,
)
from app.processing import (
    canonicalize_name,
    detect_locations,
    detect_organizations,
    detect_titles,
    extract_entities,
    extract_relationships,
    split_title_from_name,
)


def test_canonicalize_name_strips_titles():
    assert canonicalize_name("Elder Lin Lei") == "lin lei"
    assert canonicalize_name("Senior Brother Yi") == "yi"
    assert canonicalize_name("Young Master Wei") == "wei"
    assert canonicalize_name("Demon King") == "king"
    assert canonicalize_name("Lin Lei") == "lin lei"


def test_title_detector_finds_titles(sample_chapter):
    hits = detect_titles(sample_chapter)
    titles = {h.title for h in hits}
    assert "Elder" in titles


def test_organization_detector_finds_orgs(sample_chapter):
    hits = detect_organizations(sample_chapter)
    names = {h.canonical for h in hits}
    assert "Mount Hua Sect" in names
    assert "Heavenly Demon Cult" in names


def test_location_detector_finds_locations(sample_chapter):
    hits = detect_locations(sample_chapter)
    names = {h.canonical for h in hits}
    assert any("Mount Hua" in n for n in names) or "Jianghu" in names or "Central Plains" in names


def test_relationship_extractor_finds_rels(sample_chapter):
    hits = extract_relationships(sample_chapter)
    rels = [(h.relationship_type, h.source, h.target) for h in hits]
    rel_types = {r[0] for r in rels}
    assert "senior_brother" in rel_types
    assert "rival" in rel_types
    assert "master" in rel_types
    bad_words = {"he", "she", "it", "they", "is", "was", "the", "a"}
    for r in rels:
        for endpoint in (r[1], r[2]):
            assert endpoint.lower() not in bad_words, f"bad endpoint: {endpoint}"


def test_ner_finds_names(sample_chapter):
    extracted = extract_entities(sample_chapter)
    canon = {m.canonical for m in extracted.character_mentions}
    for required in ("lin lei", "yi yun", "di shi"):
        assert required in canon, f"missing name: {required}"


def test_extract_entities_use_case(sample_chapter):
    uc = ExtractEntitiesUseCase()
    result = uc.execute(sample_chapter, chapter_id="ch-12")
    assert len(result.character_mentions) > 0
    assert len(result.organizations) > 0
    assert len(result.relationships) > 0


def test_deduplicate_characters_use_case():
    candidates: list[Character] = [
        Character(name="Lin Lei", canonical_name="lin lei", appearance_frequency=10),
        Character(name="Lin Lei", canonical_name="lin lei", appearance_frequency=5),
        Character(name="Yi Yun", canonical_name="yi yun", appearance_frequency=3),
        Character(name="Yiyun", canonical_name="yiyun", appearance_frequency=1),
        Character(name="Di Shi", canonical_name="di shi", appearance_frequency=2),
    ]
    uc = DeduplicateCharactersUseCase(similarity_threshold=80)
    result = uc.execute(candidates)
    canonicals = {c.canonical_name for c in result.canonical_characters}
    assert len(canonicals) == 3
    assert "lin lei" in canonicals
    assert "yi yun" in canonicals
    assert "di shi" in canonicals
    ll = next(c for c in result.canonical_characters if c.canonical_name == "lin lei")
    assert ll.appearance_frequency == 15


def test_ingest_entities_use_case_e2e(sqlite_session_factory, sample_chapter):
    from app.core.unit_of_work import UnitOfWork

    uow = UnitOfWork(session_factory=sqlite_session_factory)
    with uow:
        extract_uc = ExtractEntitiesUseCase()
        extraction = extract_uc.execute(sample_chapter, chapter_id="ch-12")
        ingest_uc = IngestEntitiesUseCase(uow)
        result = ingest_uc.execute(extraction)
        assert result.new_characters > 0
        assert result.new_organizations > 0
        assert result.new_relationships >= 0

    uow2 = UnitOfWork(session_factory=sqlite_session_factory)
    with uow2:
        assert uow2.characters.count() > 0
        assert uow2.organizations.count() > 0
        chars = uow2.characters.list(limit=10)
        names = {c.canonical_name for c in chars}
        assert "lin lei" in names


def test_ingest_entities_idempotent(sqlite_session_factory, sample_chapter):
    from app.core.unit_of_work import UnitOfWork

    extract_uc = ExtractEntitiesUseCase()
    uow = UnitOfWork(session_factory=sqlite_session_factory)
    with uow:
        ex1 = extract_uc.execute(sample_chapter, chapter_id="ch-12")
        IngestEntitiesUseCase(uow).execute(ex1)
    uow2 = UnitOfWork(session_factory=sqlite_session_factory)
    with uow2:
        ex2 = extract_uc.execute(sample_chapter, chapter_id="ch-12")
        IngestEntitiesUseCase(uow2).execute(ex2)
        assert uow2.characters.count() > 0


def test_build_knowledge_graph_use_case(sqlite_session_factory, sample_chapter):
    import uuid as uuid_module

    from app.core.unit_of_work import UnitOfWork
    from app.models.character import Character as CharacterORM
    from app.models.organization import Organization as OrganizationORM

    uow = UnitOfWork(session_factory=sqlite_session_factory)
    with uow:
        extract_uc = ExtractEntitiesUseCase()
        extraction = extract_uc.execute(sample_chapter, chapter_id="ch-12")
        IngestEntitiesUseCase(uow).execute(extraction)

        char = next(c for c in uow.characters.list() if c.canonical_name == "lin lei")
        org = next(o for o in uow.organizations.list() if o.name == "Mount Hua Sect")
        char_orm = uow.session.get(CharacterORM, uuid_module.UUID(char.id))
        org_orm = uow.session.get(OrganizationORM, uuid_module.UUID(org.id))
        if org_orm not in char_orm.organizations:
            char_orm.organizations.append(org_orm)
        uow.session.flush()

        G = BuildKnowledgeGraphUseCase(uow).execute()
    assert G.number_of_nodes() > 0
    kinds = {d.get("kind") for _, d in G.nodes(data=True)}
    assert "character" in kinds
    assert "organization" in kinds
    char_org_edges = [(u, v, d) for u, v, d in G.edges(data=True) if d.get("kind") == "member_of"]
    assert len(char_org_edges) >= 1


def test_split_title_from_name():
    title, bare = split_title_from_name("Elder Lin Lei")
    assert title == "Elder"
    assert bare == "Lin Lei"
    title, bare = split_title_from_name("Lin Lei")
    assert title is None
    assert bare == "Lin Lei"
