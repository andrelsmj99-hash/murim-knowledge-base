from __future__ import annotations

from tests.conftest import requires_encoder


def test_health(api_client) -> None:
    client, _ = api_client
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_novel_crud_and_chapters(api_client) -> None:
    client, _ = api_client
    r = client.post(
        "/api/v1/novels",
        json={"title": "Coiling Dragon", "author": "I Eat Tomatoes", "language": "en"},
    )
    assert r.status_code == 201
    novel = r.json()
    assert novel["id"]
    novel_id = novel["id"]

    r2 = client.post(
        "/api/v1/novels",
        json={"title": "Coiling Dragon", "author": "I Eat Tomatoes", "language": "en"},
    )
    assert r2.json()["id"] == novel_id

    r = client.get(f"/api/v1/novels/{novel_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Coiling Dragon"

    for n in range(1, 4):
        r = client.post(
            f"/api/v1/novels/{novel_id}/chapters",
            json={"chapter_number": n, "title": f"Chapter {n}", "content": f"Body {n}. " * 50},
        )
        assert r.status_code == 201

    r = client.get(f"/api/v1/novels/{novel_id}/chapters")
    assert r.status_code == 200
    items = r.json()["items"]
    assert [c["chapter_number"] for c in items] == [1, 2, 3]

    r = client.get(f"/api/v1/novels/{novel_id}/chapters/2")
    assert r.status_code == 200
    assert "Body 2." in r.json()["content"]

    r = client.get("/api/v1/novels/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_novel_stats(api_client) -> None:
    client, _ = api_client
    r = client.post(
        "/api/v1/novels",
        json={"title": "Test Novel", "author": "Author", "language": "en"},
    )
    assert r.status_code == 201
    novel_id = r.json()["id"]

    # Add 2 chapters
    for n in range(1, 3):
        client.post(
            f"/api/v1/novels/{novel_id}/chapters",
            json={"chapter_number": n, "content": f"Body {n}. " * 50},
        )

    r = client.get(f"/api/v1/novels/{novel_id}/stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["novel_id"] == novel_id
    assert stats["title"] == "Test Novel"
    assert stats["chapters"] == 2
    assert stats["total_chapters_expected"] >= 1  # updated by add_chapter
    assert isinstance(stats["characters"], int)
    assert isinstance(stats["organizations"], int)
    assert isinstance(stats["locations"], int)
    assert isinstance(stats["relationships"], int)

    # 404 for non-existent novel
    r = client.get("/api/v1/novels/00000000-0000-0000-0000-000000000000/stats")
    assert r.status_code == 404


def test_character_crud_and_extras(api_client) -> None:
    client, _ = api_client
    r1 = client.post("/api/v1/characters", json={"name": "Lin Lei"})
    assert r1.status_code == 201
    char1 = r1.json()

    r2 = client.post("/api/v1/characters", json={"name": "Yi Yun"})
    assert r2.status_code == 201
    char2 = r2.json()

    r = client.get(f"/api/v1/characters/{char1['id']}")
    assert r.status_code == 200
    assert r.json()["canonical_name"] == "lin lei"

    r = client.patch(
        f"/api/v1/characters/{char1['id']}",
        json={"gender": "male", "description": "Protagonist"},
    )
    assert r.status_code == 200
    assert r.json()["gender"] == "male"

    r = client.post(
        f"/api/v1/characters/{char1['id']}/aliases",
        json={"alias_type": "Nickname", "alias_value": "Lei"},
    )
    assert r.status_code == 201
    r = client.get(f"/api/v1/characters/{char1['id']}")
    assert any(a["alias_value"] == "Lei" for a in r.json()["aliases"])

    r = client.post(
        f"/api/v1/characters/{char1['id']}/titles",
        json={"title": "Elder"},
    )
    assert r.status_code == 201
    r = client.get(f"/api/v1/characters/{char1['id']}")
    assert "Elder" in r.json()["titles"]

    r = client.post(
        f"/api/v1/characters/{char1['id']}/relationships",
        json={"related_character_id": char2["id"], "relationship_type": "senior_brother"},
    )
    assert r.status_code == 201
    r = client.get(f"/api/v1/characters/{char1['id']}")
    assert r.json()["relationships"]["senior_brother"] == [char2["id"]]

    r = client.post(
        f"/api/v1/characters/{char1['id']}/relationships",
        json={"related_character_id": char1["id"], "relationship_type": "rival"},
    )
    assert r.status_code == 400

    r = client.delete(f"/api/v1/characters/{char2['id']}")
    assert r.status_code == 204
    r = client.get(f"/api/v1/characters/{char2['id']}")
    assert r.status_code == 404


def test_organization_crud_and_relationships(api_client) -> None:
    client, _ = api_client
    a = client.post("/api/v1/organizations", json={"name": "Mount Hua Sect", "type": "Sect"}).json()
    b = client.post(
        "/api/v1/organizations", json={"name": "Heavenly Demon Cult", "type": "Cult"}
    ).json()
    c = client.post(
        "/api/v1/organizations", json={"name": "Righteous Alliance", "type": "Alliance"}
    ).json()

    r = client.post(
        f"/api/v1/organizations/{a['id']}/relationships",
        json={"related_organization_id": b["id"], "relationship_type": "rival"},
    )
    assert r.status_code == 201
    r = client.post(
        f"/api/v1/organizations/{a['id']}/relationships",
        json={"related_organization_id": c["id"], "relationship_type": "ally"},
    )
    assert r.status_code == 201

    rivals = client.get(f"/api/v1/organizations/{a['id']}/rivals").json()
    allies = client.get(f"/api/v1/organizations/{a['id']}/allies").json()
    assert {r["name"] for r in rivals} == {"Heavenly Demon Cult"}
    assert {r["name"] for r in allies} == {"Righteous Alliance"}


def test_location_crud_and_hierarchy(api_client) -> None:
    client, _ = api_client
    realm = client.post(
        "/api/v1/locations",
        json={"name": "Central Plains", "type": "Region"},
    ).json()
    city = client.post(
        "/api/v1/locations",
        json={"name": "Imperial City", "type": "City", "parent_location_id": realm["id"]},
    ).json()
    sub = client.get(f"/api/v1/locations/{realm['id']}/sub-locations").json()
    assert any(loc["id"] == city["id"] for loc in sub)


def test_character_location_linking(api_client) -> None:
    client, _ = api_client
    c = client.post("/api/v1/characters", json={"name": "Chung Myung"}).json()
    loc = client.post("/api/v1/locations", json={"name": "Mount Hua", "type": "Mountain"}).json()

    r = client.get(f"/api/v1/characters/{c['id']}")
    assert r.json()["locations"] == []

    r = client.post(f"/api/v1/characters/{c['id']}/locations", json={"location_id": loc["id"]})
    assert r.status_code == 201
    assert loc["id"] in r.json()["locations"]

    r = client.get(f"/api/v1/characters/{c['id']}")
    assert loc["id"] in r.json()["locations"]

    r = client.delete(f"/api/v1/characters/{c['id']}/locations/{loc['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/v1/characters/{c['id']}")
    assert r.json()["locations"] == []


def test_character_location_link_404(api_client) -> None:
    client, _ = api_client
    r = client.post(
        "/api/v1/characters/00000000-0000-0000-0000-000000000000/locations",
        json={"location_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 404


def test_character_organization_linking(api_client) -> None:
    client, _ = api_client
    c = client.post("/api/v1/characters", json={"name": "Chung Myung"}).json()
    org = client.post(
        "/api/v1/organizations", json={"name": "Mount Hua Sect", "type": "Sect"}
    ).json()

    r = client.get(f"/api/v1/characters/{c['id']}")
    assert r.json()["organizations"] == []

    r = client.post(
        f"/api/v1/characters/{c['id']}/organizations",
        json={"organization_id": org["id"]},
    )
    assert r.status_code == 201
    assert org["id"] in r.json()["organizations"]

    r = client.get(f"/api/v1/characters/{c['id']}")
    assert org["id"] in r.json()["organizations"]

    r = client.delete(f"/api/v1/characters/{c['id']}/organizations/{org['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/v1/characters/{c['id']}")
    assert r.json()["organizations"] == []


def test_character_organization_link_404(api_client) -> None:
    client, _ = api_client
    r = client.post(
        "/api/v1/characters/00000000-0000-0000-0000-000000000000/organizations",
        json={"organization_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 404


def test_scrape_endpoint_unknown_source(api_client) -> None:
    client, _ = api_client
    r = client.post(
        "/api/v1/scrape",
        json={
            "source": "nonexistent",
            "novel_slug": "test",
            "index_url": "http://example.com",
            "base_url": "http://example.com",
        },
    )
    assert r.status_code == 400


def _mock_response(content: str, status: int = 200) -> type:
    import requests

    mock_resp = requests.Response()
    mock_resp.status_code = status
    mock_resp._content = content.encode("utf-8")
    return mock_resp


def test_scrape_endpoint_happy_path(api_client, monkeypatch) -> None:
    client, _ = api_client

    index_html = """
    <html><body>
    <ul class="chapter-list">
        <li><a href="/ch1">Chapter 1 — Start</a></li>
        <li><a href="/ch2">Chapter 2 — Middle</a></li>
    </ul>
    </body></html>
    """
    chapter_html = (
        "<html><body><div id='chapter-content'><p>Some text content.</p></div></body></html>"
    )

    call_count = 0

    def fake_make_request(self, url, **kwargs):
        nonlocal call_count
        call_count += 1
        if "ch1" in url or "ch2" in url:
            return _mock_response(chapter_html)
        return _mock_response(index_html)

    monkeypatch.setattr("app.scrapers.generic.GenericScraper._make_request", fake_make_request)

    r = client.post(
        "/api/v1/scrape",
        json={
            "source": "generic",
            "novel_slug": "test-novel",
            "index_url": "http://example.com/novel",
            "base_url": "http://example.com",
            "reverse_chapter_list": False,
            "resume": False,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert not body["errors"]
    assert len(body["chapters"]) == 2


def test_scrape_endpoint_no_chapters(api_client, monkeypatch) -> None:
    client, _ = api_client
    html = "<html><body><p>No chapters here</p></body></html>"

    def fake_make_request(self, url, **kwargs):
        return _mock_response(html)

    monkeypatch.setattr("app.scrapers.generic.GenericScraper._make_request", fake_make_request)

    r = client.post(
        "/api/v1/scrape",
        json={
            "source": "generic",
            "novel_slug": "empty-novel",
            "index_url": "http://example.com/empty",
            "base_url": "http://example.com",
        },
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


@requires_encoder
def test_character_embed_single(api_client) -> None:
    client, _ = api_client
    r = client.post(
        "/api/v1/characters", json={"name": "Lin Lei", "description": "The protagonist"}
    )
    assert r.status_code == 201
    char_id = r.json()["id"]

    r = client.post(f"/api/v1/characters/{char_id}/embed")
    assert r.status_code == 200
    assert r.json()["has_embedding"] is True


@requires_encoder
def test_character_embed_all(api_client) -> None:
    client, _ = api_client
    client.post("/api/v1/characters", json={"name": "Lin Lei"})
    client.post("/api/v1/characters", json={"name": "Yi Yun"})
    client.post("/api/v1/characters", json={"name": "Di Shi"})

    r = client.post("/api/v1/characters/embed-all")
    assert r.status_code == 200
    assert r.json()["success"] == 3


def test_character_embed_404(api_client) -> None:
    client, _ = api_client
    r = client.post("/api/v1/characters/00000000-0000-0000-0000-000000000000/embed")
    assert r.status_code == 404


def test_search_lexical_fallback(api_client) -> None:
    client, _ = api_client
    client.post("/api/v1/characters", json={"name": "Lin Lei"})
    client.post("/api/v1/characters", json={"name": "Linlei"})
    client.post("/api/v1/organizations", json={"name": "Mount Hua Sect", "type": "Sect"})

    r = client.get("/api/v1/search", params={"q": "lin", "limit": 10, "semantic": False})
    assert r.status_code == 200
    assert "character" in {h["kind"] for h in r.json()["hits"]}


@requires_encoder
def test_search_semantic(api_client) -> None:
    client, _ = api_client
    r1 = client.post(
        "/api/v1/characters", json={"name": "Lin Lei", "description": "A powerful swordsman"}
    )
    r2 = client.post(
        "/api/v1/characters", json={"name": "Yi Yun", "description": "A young cultivator"}
    )
    char1 = r1.json()
    char2 = r2.json()

    # Embed both characters
    client.post(f"/api/v1/characters/{char1['id']}/embed")
    client.post(f"/api/v1/characters/{char2['id']}/embed")

    # Semantic search should return results
    r = client.get("/api/v1/search", params={"q": "sword", "limit": 10, "semantic": True})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(h["kind"] == "character" for h in body["hits"])


def test_graph_serialization(api_client) -> None:
    client, _ = api_client
    client.post("/api/v1/novels", json={"title": "Foo", "language": "en"})
    c = client.post("/api/v1/characters", json={"name": "Lin Lei"}).json()
    o = client.post("/api/v1/organizations", json={"name": "Mount Hua Sect", "type": "Sect"}).json()

    # Link character to organization via API
    r_link = client.post(
        f"/api/v1/characters/{c['id']}/organizations",
        json={"organization_id": o["id"]},
    )
    assert r_link.status_code == 201

    r = client.get("/api/v1/graph")
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["characters"] >= 1
    assert body["stats"]["organizations"] >= 1
    assert any(e["kind"] == "member_of" for e in body["edges"])


# ── List endpoint pagination ──


def test_list_characters_pagination(api_client) -> None:
    client, _ = api_client
    for i in range(5):
        client.post("/api/v1/characters", json={"name": f"Char {i}"})

    r = client.get("/api/v1/characters", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["meta"]["total"] >= 5

    r2 = client.get("/api/v1/characters", params={"limit": 2, "offset": 4})
    assert r2.status_code == 200
    assert len(r2.json()["items"]) >= 1


def test_list_organizations_pagination(api_client) -> None:
    client, _ = api_client
    for i in range(4):
        client.post("/api/v1/organizations", json={"name": f"Org {i}", "type": "Sect"})

    r = client.get("/api/v1/organizations", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["meta"]["total"] >= 4


def test_list_locations_pagination(api_client) -> None:
    client, _ = api_client
    for i in range(3):
        client.post("/api/v1/locations", json={"name": f"Loc {i}", "type": "City"})

    r = client.get("/api/v1/locations", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["meta"]["total"] >= 3


# ── Error paths ──


def test_character_not_found_404(api_client) -> None:
    client, _ = api_client
    r = client.get("/api/v1/characters/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_organization_not_found_404(api_client) -> None:
    client, _ = api_client
    r = client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_location_not_found_404(api_client) -> None:
    client, _ = api_client
    r = client.get("/api/v1/locations/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_organization_relationship_duplicate_409(api_client) -> None:
    client, _ = api_client
    a = client.post("/api/v1/organizations", json={"name": "Sect A", "type": "Sect"}).json()
    b = client.post("/api/v1/organizations", json={"name": "Sect B", "type": "Sect"}).json()

    r1 = client.post(
        f"/api/v1/organizations/{a['id']}/relationships",
        json={"related_organization_id": b["id"], "relationship_type": "rival"},
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/v1/organizations/{a['id']}/relationships",
        json={"related_organization_id": b["id"], "relationship_type": "rival"},
    )
    assert r2.status_code == 409


def test_organization_relationship_not_found_404(api_client) -> None:
    client, _ = api_client
    a = client.post("/api/v1/organizations", json={"name": "Sect A", "type": "Sect"}).json()
    r = client.post(
        f"/api/v1/organizations/{a['id']}/relationships",
        json={
            "related_organization_id": "00000000-0000-0000-0000-000000000000",
            "relationship_type": "rival",
        },
    )
    assert r.status_code == 404


def test_organization_rivals_not_found_404(api_client) -> None:
    client, _ = api_client
    r = client.get("/api/v1/organizations/00000000-0000-0000-0000-000000000000/rivals")
    assert r.status_code == 404


def test_character_patch_not_found_404(api_client) -> None:
    client, _ = api_client
    r = client.patch(
        "/api/v1/characters/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
    )
    assert r.status_code == 404


def test_character_delete_not_found_404(api_client) -> None:
    client, _ = api_client
    r = client.delete("/api/v1/characters/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
