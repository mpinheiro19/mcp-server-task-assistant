import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse

from mcp_assistant.api.auth.dependencies import get_current_user, make_session_cookie
from mcp_assistant.api.models.auth import UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


def _oauth2_enabled() -> bool:
    return os.getenv("ENABLE_OAUTH2", "false").lower() == "true"


@router.get("/login")
async def login() -> Response:
    if not _oauth2_enabled():
        return Response(content='{"enabled": false}', media_type="application/json")

    params = {
        "client_id": os.getenv("OAUTH2_CLIENT_ID", ""),
        "redirect_uri": os.getenv("OAUTH2_CALLBACK_URL", "http://localhost:8000/auth/callback"),
        "scope": "read:user user:email",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    authorize_url = os.getenv("OAUTH2_AUTHORIZE_URL", "https://github.com/login/oauth/authorize")
    return RedirectResponse(url=f"{authorize_url}?{query}")


@router.get("/callback")
async def callback(code: str, response: Response) -> Response:
    if not _oauth2_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OAuth2 not enabled")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            os.getenv("OAUTH2_TOKEN_URL", "https://github.com/login/oauth/access_token"),
            data={
                "client_id": os.getenv("OAUTH2_CLIENT_ID", ""),
                "client_secret": os.getenv("OAUTH2_CLIENT_SECRET", ""),
                "code": code,
                "redirect_uri": os.getenv(
                    "OAUTH2_CALLBACK_URL", "http://localhost:8000/auth/callback"
                ),
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")

        userinfo_resp = await client.get(
            os.getenv("OAUTH2_USERINFO_URL", "https://api.github.com/user"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    user = UserInfo(
        sub=str(userinfo.get("id", "")),
        login=userinfo.get("login", ""),
        name=userinfo.get("name"),
        email=userinfo.get("email"),
        avatar_url=userinfo.get("avatar_url"),
    )

    cookie_value = make_session_cookie(user)
    redirect_url = os.getenv("OAUTH2_REDIRECT_AFTER_LOGIN", "/")
    resp = RedirectResponse(url=redirect_url)
    resp.set_cookie(
        key="session",
        value=cookie_value,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return resp


@router.get("/me")
async def me(user: UserInfo | None = Depends(get_current_user)) -> Response:
    if not _oauth2_enabled():
        from fastapi.responses import JSONResponse

        return JSONResponse({"auth_enabled": False})
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("session")
    return {"logged_out": True}
