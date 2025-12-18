import json
import time
from collections.abc import Iterable
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.algorithms import RSAAlgorithm
from jwt.utils import base64url_decode

bearer = HTTPBearer(auto_error=True)


class JWKSCache:
    def __init__(self, url: str, cache_ttl_seconds: int = 300):
        self.url = url
        self.cache_ttl_seconds = cache_ttl_seconds
        self._keys: dict[str, dict[str, Any]] = {}
        self._exp = 0.0

    def get_keys(self) -> dict[str, dict[str, Any]]:
        now = time.time()
        if self._keys and now < self._exp:
            return self._keys

        with httpx.Client(timeout=5.0) as client:
            resp = client.get(self.url)
            resp.raise_for_status()
            payload = resp.json()

        self._keys = {k.get("kid"): k for k in payload.get("keys", []) if k.get("kid")}
        self._exp = now + self.cache_ttl_seconds
        return self._keys


class AuthVerifier:
    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: str,
        cache_ttl_seconds: int = 300,
        allowed_algs: Iterable[str] | None = None,
        clock_skew_seconds: int = 30,
    ):
        self.issuer = issuer
        self.audience = audience
        self.jwks = JWKSCache(jwks_url, cache_ttl_seconds)
        self.allowed_algs: set[str] = set(allowed_algs or {"RS256"})
        self.clock_skew_seconds = clock_skew_seconds

    def __call__(self, creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict[str, Any]:
        token = creds.credentials
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header") from exc

        kid = unverified_header.get("kid")
        typ = unverified_header.get("typ", "JWT")
        alg = unverified_header.get("alg")
        if typ.upper() != "JWT":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        if alg not in self.allowed_algs:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token algorithm")
        key_data = self.jwks.get_keys().get(kid)
        if not key_data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key")

        try:
            if key_data.get("kty") == "oct":
                # Symmetric JWKS entry: decode shared secret
                key = base64url_decode(key_data["k"].encode())
            else:
                key = RSAAlgorithm.from_jwk(json.dumps(key_data))

            claims = jwt.decode(
                token,
                key=key,
                algorithms=list(self.allowed_algs),
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={"require": ["exp", "iss", "aud"]},
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        return claims


def require_scope(scope: str, verifier: AuthVerifier):
    def dependency(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict[str, Any]:
        claims = verifier(credentials)
        roles = claims.get("realm_access", {}).get("roles", [])
        if scope not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
        return claims

    return dependency
