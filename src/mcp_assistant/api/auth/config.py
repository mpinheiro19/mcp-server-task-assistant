import os


class AuthConfig:
    ENABLE_OAUTH2 = os.getenv("ENABLE_OAUTH2", "false").lower() == "true"
    CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET", "")
    # GitHub defaults — swap to any OIDC provider via env vars
    AUTHORIZE_URL = os.getenv(
        "OAUTH2_AUTHORIZE_URL", "https://github.com/login/oauth/authorize"
    )
    TOKEN_URL = os.getenv(
        "OAUTH2_TOKEN_URL", "https://github.com/login/oauth/access_token"
    )
    USERINFO_URL = os.getenv("OAUTH2_USERINFO_URL", "https://api.github.com/user")
    SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "change-me-in-production")
    CALLBACK_URL = os.getenv("OAUTH2_CALLBACK_URL", "http://localhost:8000/auth/callback")
