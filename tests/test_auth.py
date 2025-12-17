import time
from typing import List

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from jose.utils import base64url_encode

from src.auth import AuthVerifier, JWKSCache, require_scope


def make_token(secret: bytes, kid: str, issuer: str, audience: str, extra: dict | None = None) -> str:
    payload = {"iss": issuer, "aud": audience, "exp": time.time() + 60}
    payload.update(extra or {})
    return jwt.encode(payload, secret, algorithm="HS256", headers={"kid": kid})


def test_jwks_cache_uses_cached_keys(monkeypatch):
    called: List[str] = []
    payload = {"keys": [{"kid": "abc", "kty": "oct", "k": base64url_encode(b"secret").decode()}]}

    class DummyResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url):
            called.append(url)
            return DummyResponse(payload)

    monkeypatch.setattr("httpx.Client", lambda timeout=5.0: DummyClient())
    monkeypatch.setattr("time.time", lambda: 100)

    cache = JWKSCache("http://fake", cache_ttl_seconds=60)

    keys_first = cache.get_keys()
    keys_second = cache.get_keys()

    assert called == ["http://fake"]
    assert keys_first == keys_second


def test_auth_verifier_accepts_valid_token(monkeypatch):
    secret = b"secret"
    kid = "kid1"
    issuer = "https://issuer"
    audience = "books-api"
    token = make_token(secret, kid, issuer, audience, {"realm_access": {"roles": ["books:read"]}})

    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}

    monkeypatch.setattr(
        AuthVerifier,
        "jwks",
        JWKSCache("http://fake"),
        raising=False,
    )
    verifier = AuthVerifier(
        issuer=issuer,
        audience=audience,
        jwks_url="http://fake",
        cache_ttl_seconds=0,
        allowed_algs={"HS256"},
    )
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    claims = verifier(creds)

    assert claims["iss"] == issuer
    assert audience in claims["aud"]


def test_auth_verifier_rejects_bad_issuer(monkeypatch):
    secret = b"secret"
    kid = "kid1"
    token = make_token(secret, kid, "https://wrong", "books-api")
    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}

    verifier = AuthVerifier(issuer="https://issuer", audience="books-api", jwks_url="http://fake", cache_ttl_seconds=0)
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verifier(creds)
    assert exc.value.status_code == 401


def test_require_scope_enforces_roles(monkeypatch):
    secret = b"secret"
    kid = "kid1"
    issuer = "https://issuer"
    audience = "books-api"
    token = make_token(
        secret,
        kid,
        issuer,
        audience,
        {"realm_access": {"roles": ["books:read"]}},
    )
    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}

    verifier = AuthVerifier(
        issuer=issuer,
        audience=audience,
        jwks_url="http://fake",
        cache_ttl_seconds=0,
        allowed_algs={"HS256"},
    )
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    dependency = require_scope("books:write", verifier)

    with pytest.raises(HTTPException) as exc:
        dependency(creds)
    assert exc.value.status_code == 403

    # Adding the required scope should allow access
    good_token = make_token(
        secret,
        kid,
        issuer,
        audience,
        {"realm_access": {"roles": ["books:read", "books:write"]}},
    )
    creds_ok = HTTPAuthorizationCredentials(scheme="Bearer", credentials=good_token)
    claims = dependency(creds_ok)
    assert "books:write" in claims["realm_access"]["roles"]


def test_auth_verifier_rejects_expired_token(monkeypatch):
    secret = b"secret"
    kid = "kid-expired"
    issuer = "https://issuer"
    audience = "books-api"
    token = jwt.encode(
        {"iss": issuer, "aud": audience, "exp": time.time() - 10},
        secret,
        algorithm="HS256",
        headers={"kid": kid},
    )
    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}
    verifier = AuthVerifier(issuer=issuer, audience=audience, jwks_url="http://fake", cache_ttl_seconds=0)
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verifier(creds)
    assert exc.value.status_code == 401


def test_auth_verifier_rejects_bad_audience(monkeypatch):
    secret = b"secret"
    kid = "kid-aud"
    issuer = "https://issuer"
    token = make_token(secret, kid, issuer, "other-aud")
    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}
    verifier = AuthVerifier(issuer=issuer, audience="books-api", jwks_url="http://fake", cache_ttl_seconds=0)
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verifier(creds)
    assert exc.value.status_code == 401


def test_auth_verifier_unknown_kid(monkeypatch):
    secret = b"secret"
    kid = "kid-unknown"
    issuer = "https://issuer"
    audience = "books-api"
    token = make_token(secret, kid, issuer, audience)
    verifier = AuthVerifier(issuer=issuer, audience=audience, jwks_url="http://fake", cache_ttl_seconds=0)
    verifier.jwks.get_keys = lambda: {}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verifier(creds)
    assert exc.value.status_code == 401


def test_auth_verifier_rejects_disallowed_alg(monkeypatch):
    secret = b"secret"
    kid = "kid-alg"
    issuer = "https://issuer"
    audience = "books-api"
    token = jwt.encode(
        {"iss": issuer, "aud": audience, "exp": time.time() + 30},
        secret,
        algorithm="HS256",
        headers={"kid": kid},
    )
    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}
    verifier = AuthVerifier(
        issuer=issuer,
        audience=audience,
        jwks_url="http://fake",
        cache_ttl_seconds=0,
        allowed_algs={"RS256"},
    )
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verifier(creds)
    assert exc.value.status_code == 401


def test_auth_verifier_rejects_typ(monkeypatch):
    secret = b"secret"
    kid = "kid-typ"
    issuer = "https://issuer"
    audience = "books-api"
    token = jwt.encode(
        {"iss": issuer, "aud": audience, "exp": time.time() + 30},
        secret,
        algorithm="HS256",
        headers={"kid": kid, "typ": "Wrong"},
    )
    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}
    verifier = AuthVerifier(
        issuer=issuer,
        audience=audience,
        jwks_url="http://fake",
        cache_ttl_seconds=0,
        allowed_algs={"HS256"},
    )
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        verifier(creds)
    assert exc.value.status_code == 401


def test_auth_verifier_respects_clock_skew(monkeypatch):
    secret = b"secret"
    kid = "kid-skew"
    issuer = "https://issuer"
    audience = "books-api"
    token = jwt.encode(
        {"iss": issuer, "aud": audience, "exp": time.time() - 5},
        secret,
        algorithm="HS256",
        headers={"kid": kid},
    )
    jwk_key = {"kty": "oct", "k": base64url_encode(secret).decode(), "kid": kid, "alg": "HS256"}
    verifier = AuthVerifier(
        issuer=issuer,
        audience=audience,
        jwks_url="http://fake",
        cache_ttl_seconds=0,
        allowed_algs={"HS256"},
        clock_skew_seconds=10,
    )
    verifier.jwks.get_keys = lambda: {kid: jwk_key}  # type: ignore[method-assign]

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    claims = verifier(creds)
    assert claims["aud"] == audience
