"""
Bearer-token authentication dependency.

This module provides a FastAPI dependency function that any protected route
can declare. When a request comes in, FastAPI runs require_bearer_token
before the route handler. If the token is missing or wrong, the request is
rejected with 401 and the route handler never executes.

Why constant-time comparison: a naive string comparison (==) returns False
as soon as it finds the first mismatched character. An attacker timing
thousands of requests can use response-time differences to recover the
token character-by-character. secrets.compare_digest takes the same time
regardless of where the mismatch is. This is paranoia, but it's free
paranoia, so we do it.
"""

import secrets

from fastapi import Header, HTTPException, status

from app.core.settings import settings


async def require_bearer_token(
    # FastAPI reads the Authorization header automatically because we annotate
    # this parameter with Header(...). The alias makes it case-insensitive.
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """
    Verify the request carries a valid bearer token.

    Raises 401 if the header is missing, malformed, or the token doesn't match
    the configured AGENT_TOKEN. Returns nothing on success — the dependency's
    only job is to fail loudly when auth is wrong.
    """
    # Missing header entirely.
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Authorization header",
            # WWW-Authenticate is the standard way to tell the client what
            # auth scheme this resource expects. Some HTTP clients use it.
            headers={"WWW-Authenticate": "Bearer"},
        )

    # The header must be of the form "Bearer <token>" — split into exactly two
    # parts on whitespace and verify the scheme.
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="malformed Authorization header; expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time compare. Note: comparing to "" if AGENT_TOKEN was never
    # set means every request fails — that's the safer default than letting
    # everyone through.
    presented_token = parts[1]
    if not secrets.compare_digest(presented_token, settings.agent_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )