import os

from fastapi import Cookie, Depends, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from mcp_assistant.api.models.auth import UserInfo


def _get_serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("SESSION_SECRET_KEY", "change-me-in-production")
    return URLSafeTimedSerializer(secret)


def get_current_user(
    session: str | None = Cookie(default=None),
) -> UserInfo | None:
    if session is None:
        return None
    try:
        serializer = _get_serializer()
        data = serializer.loads(session, max_age=86400)  # 24h
        return UserInfo(**data)
    except (BadSignature, SignatureExpired, Exception):
        return None


def require_auth(user: UserInfo | None = Depends(get_current_user)) -> UserInfo:
    oauth2_enabled = os.getenv("ENABLE_OAUTH2", "false").lower() == "true"
    if not oauth2_enabled:
        # Return a synthetic anonymous user when auth is disabled
        return UserInfo(sub="anonymous", login="anonymous")
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


def make_session_cookie(user: UserInfo) -> str:
    serializer = _get_serializer()
    return serializer.dumps(user.model_dump())
