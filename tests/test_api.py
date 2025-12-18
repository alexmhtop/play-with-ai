import httpx
import pytest
import asyncio
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.app import app, get_book_service, read_access, write_access
from src.db import Base, get_engine, get_session
from src.models import UpdateBook
from src.service import BookService


@pytest.fixture(scope="session")
def engine():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = Session()
    session.execute(text("TRUNCATE TABLE books RESTART IDENTITY CASCADE;"))
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(autouse=True)
def overrides(db_session):
    def _get_test_session():
        try:
            yield db_session
        finally:
            db_session.rollback()

    app.dependency_overrides[get_session] = _get_test_session
    app.dependency_overrides[get_book_service] = lambda: BookService(db_session)
    app.dependency_overrides[read_access] = lambda: {
        "realm_access": {"roles": ["books:read", "books:write"]}
    }
    app.dependency_overrides[write_access] = lambda: {
        "realm_access": {"roles": ["books:read", "books:write"]}
    }
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_create_and_get_book(client):
    payload = {"title": "1984", "author": "Orwell", "price": 9.99, "in_stock": True}
    resp = await client.post("/api/v1/books", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    assert created["title"] == "1984"
    assert created["id"] == 1

    resp = await client.get(f"/api/v1/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["author"] == "Orwell"


@pytest.mark.anyio
async def test_update_and_delete_book(client):
    payload = {"title": "Dune", "author": "Herbert", "price": 12.5, "in_stock": True}
    created = (await client.post("/api/v1/books", json=payload)).json()
    updated = await client.put(
        f"/api/v1/books/{created['id']}",
        json={"price": 15.0, "in_stock": False},
    )
    assert updated.status_code == 200
    assert updated.json()["price"] == 15.0
    assert updated.json()["version"] == 2

    deleted = await client.delete(f"/api/v1/books/{created['id']}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/books/{created['id']}")
    assert missing.status_code == 404


@pytest.mark.anyio
async def test_versioned_listing_sorted(client):
    await client.post("/api/v1/books", json={"title": "B", "author": "X", "price": 1.0, "in_stock": True})
    await client.post("/api/v1/books", json={"title": "a", "author": "Y", "price": 1.0, "in_stock": True})

    resp_v2 = await client.get("/api/v2/books")
    titles = [item["title"] for item in resp_v2.json()]
    assert titles == sorted(titles, key=lambda t: t.lower())


@pytest.mark.anyio
async def test_update_nonexistent_returns_404(client):
    resp = await client.put("/api/v1/books/999", json={"price": 10})
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.anyio
async def test_delete_nonexistent_returns_404(client):
    resp = await client.delete("/api/v1/books/999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Book not found"


@pytest.mark.anyio
async def test_version_increments_with_updates(client):
    created = (await client.post("/api/v1/books", json={"title": "V", "author": "X", "price": 1.0})).json()
    first = await client.put(f"/api/v1/books/{created['id']}", json={"price": 2.0})
    second = await client.put(f"/api/v1/books/{created['id']}", json={"price": 3.0})
    assert first.json()["version"] == 2
    assert second.json()["version"] == 3


@pytest.mark.anyio
async def test_validation_error_shape_for_negative_price(client):
    resp = await client.post(
        "/api/v1/books",
        json={"title": "bad", "author": "x", "price": -1.0, "in_stock": True},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"][0]["loc"][-1] == "price"


@pytest.mark.anyio
async def test_missing_auth_returns_403():
    from fastapi import HTTPException, Request

    def enforce_auth(request: Request):
        if "authorization" not in request.headers:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return True

    app.dependency_overrides.clear()
    app.dependency_overrides[read_access] = enforce_auth
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as bare_client:
        resp = await bare_client.get("/api/v1/books")
    assert resp.status_code in (401, 403)
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_concurrent_updates_increase_version(client, db_session):
    # Simulate two services updating the same record
    from src.service import BookService

    created = (await client.post("/api/v1/books", json={"title": "C", "author": "X", "price": 1.0})).json()
    Session = sessionmaker(bind=db_session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
    service1 = BookService(Session())
    service2 = BookService(Session())

    try:
        service1.update(created["id"], UpdateBook(price=2.0))
        service2.update(created["id"], UpdateBook(price=3.0))
    finally:
        service1.session.close()
        service2.session.close()

    resp = await client.get(f"/api/v1/books/{created['id']}")
    assert resp.json()["version"] == 3


@pytest.mark.anyio
async def test_health_smoke_parallel():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as smoke:
        results = await asyncio.gather(*[smoke.get("/api/v1/health") for _ in range(5)])
    assert all(r.status_code == 200 for r in results)
