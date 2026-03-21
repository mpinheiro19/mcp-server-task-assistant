from pydantic import BaseModel


class UserInfo(BaseModel):
    sub: str
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class TokenInfo(BaseModel):
    access_token: str
    token_type: str = "bearer"
