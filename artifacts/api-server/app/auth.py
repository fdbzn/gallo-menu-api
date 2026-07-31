"""JWT validation for Supabase Auth.

Supports:
- ES256 / RS256 via project JWKS (current Supabase signing keys)
- HS256 via SUPABASE_JWT_SECRET (legacy secret + local tests)
"""
from __future__ import annotations

import time
from typing import Any

import httpx
from jose import JWTError, jwk, jwt

from app.config import settings

HS256 = "HS256"
ASYMMETRIC_ALGS = frozenset({"ES256", "RS256"})
_JWKS_TTL_SECONDS = 3600.0
_jwks_cache: dict[str, Any] = {"keys": [], "fetched_at": 0.0}


def clear_jwks_cache() -> None:
    """Reset JWKS cache (tests / key rotation)."""
    _jwks_cache["keys"] = []
    _jwks_cache["fetched_at"] = 0.0


def _jwks_url() -> str:
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


def _fetch_jwks(*, force: bool = False) -> list[dict]:
    now = time.monotonic()
    if (
        not force
        and _jwks_cache["keys"]
        and now - float(_jwks_cache["fetched_at"]) < _JWKS_TTL_SECONDS
    ):
        return list(_jwks_cache["keys"])

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(_jwks_url())
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise JWTError(f"Failed to fetch JWKS: {exc}") from exc

    keys = payload.get("keys") or []
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return list(keys)


def _decode_with_secret(token: str) -> dict:
    return jwt.decode(
        token,
        settings.supabase_jwt_secret,
        algorithms=[HS256],
        options={"verify_aud": False},
    )


def _find_jwk(keys: list[dict], kid: str | None) -> dict | None:
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
        return None
    return keys[0] if len(keys) == 1 else None


def _decode_with_jwks(token: str, header: dict) -> dict:
    kid = header.get("kid")
    alg = header.get("alg") or "ES256"
    keys = _fetch_jwks()
    jwk_data = _find_jwk(keys, kid)
    if jwk_data is None:
        keys = _fetch_jwks(force=True)
        jwk_data = _find_jwk(keys, kid)
    if jwk_data is None:
        raise JWTError("No matching JWK found for token kid")

    key = jwk.construct(jwk_data)
    return jwt.decode(
        token,
        key,
        algorithms=[alg],
        options={"verify_aud": False},
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT.
    Returns the full claims dict on success.
    Raises JWTError on failure.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise
    except Exception as exc:
        raise JWTError(str(exc)) from exc

    alg = header.get("alg")
    if alg == HS256:
        return _decode_with_secret(token)

    if alg in ASYMMETRIC_ALGS or header.get("kid"):
        return _decode_with_jwks(token, header)

    return _decode_with_secret(token)
