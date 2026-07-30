"""JWT validation using Supabase JWT secret."""
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def decode_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT.
    Returns the full claims dict on success.
    Raises JWTError on failure.
    """
    try:
        claims = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
        return claims
    except JWTError as exc:
        raise exc
