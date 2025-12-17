import time
from typing import Any, Dict, Iterable, Set

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk, jwt
from jose.utils import base64url_decode

bearer = HTTPBearer(auto_error=True)


class JWKSCache:
    def __init__(self, url: str, cache_ttl_seconds: int = 300):
        self.url = url
        self.cache_ttl_seconds = cache_ttl_seconds
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._exp = 0.0

    def get_keys(self) -> Dict[str, Dict[str, Any]]:
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
        self.allowed_algs: Set[str] = set(allowed_algs or {"RS256"})
        self.clock_skew_seconds = clock_skew_seconds

    def __call__(self, creds: HTTPAuthorizationCredentials = Depends(bearer)) -> Dict[str, Any]:
        token = creds.credentials
        try:
            unverified_header = jwt.get_unverified_header(token)
        except Exception as exc:  # noqa: BLE001
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
            public_key = jwk.construct(key_data)
            message, encoded_sig = token.rsplit(".", 1)
            decoded_sig = base64url_decode(encoded_sig.encode())
            if not public_key.verify(message.encode(), decoded_sig):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad signature")
            claims = jwt.get_unverified_claims(token)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        if claims.get("iss") != self.issuer:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad issuer")

        aud_claim = claims.get("aud")
        audiences = [aud_claim] if isinstance(aud_claim, str) else aud_claim or []
        if self.audience not in audiences:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad audience")

        if time.time() > claims.get("exp", 0) + self.clock_skew_seconds:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

        return claims


def require_scope(scope: str, verifier: AuthVerifier):
    def dependency(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> Dict[str, Any]:
        claims = verifier(credentials)
        roles = claims.get("realm_access", {}).get("roles", [])
        if scope not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
        return claims

    return dependency
