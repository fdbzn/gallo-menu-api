"""Unit tests for JWT decode (HS256 secret + ES256 JWKS)."""
import time
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jose import JWTError, jwk, jwt

from app.auth import clear_jwks_cache, decode_token
from app.config import settings


def _es256_pair():
    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_jwk = jwk.construct(pub_pem, algorithm="ES256").to_dict()
    pub_jwk["kid"] = "test-es256-kid"
    pub_jwk["alg"] = "ES256"
    pub_jwk["use"] = "sig"
    return priv_pem, pub_jwk


@pytest.fixture(autouse=True)
def _reset_jwks_cache():
    clear_jwks_cache()
    yield
    clear_jwks_cache()


def test_decode_hs256_with_secret():
    token = jwt.encode(
        {
            "sub": "user-hs",
            "email": "hs@example.com",
            "aud": "authenticated",
            "role": "authenticated",
        },
        settings.supabase_jwt_secret,
        algorithm="HS256",
    )
    claims = decode_token(token)
    assert claims["sub"] == "user-hs"
    assert claims["email"] == "hs@example.com"


def test_decode_es256_with_jwks():
    priv_pem, pub_jwk = _es256_pair()
    token = jwt.encode(
        {
            "sub": "user-es",
            "email": "es@example.com",
            "aud": "authenticated",
            "role": "authenticated",
            "exp": int(time.time()) + 3600,
        },
        priv_pem,
        algorithm="ES256",
        headers={"kid": pub_jwk["kid"]},
    )

    with patch("app.auth._fetch_jwks", return_value=[pub_jwk]):
        claims = decode_token(token)

    assert claims["sub"] == "user-es"
    assert claims["email"] == "es@example.com"


def test_decode_es256_rejects_unknown_kid():
    priv_pem, pub_jwk = _es256_pair()
    token = jwt.encode(
        {
            "sub": "user-es",
            "aud": "authenticated",
            "role": "authenticated",
            "exp": int(time.time()) + 3600,
        },
        priv_pem,
        algorithm="ES256",
        headers={"kid": "other-kid"},
    )

    with patch("app.auth._fetch_jwks", return_value=[pub_jwk]):
        with pytest.raises(JWTError):
            decode_token(token)


def test_decode_rejects_invalid_token():
    with pytest.raises(JWTError):
        decode_token("not-a-jwt")
