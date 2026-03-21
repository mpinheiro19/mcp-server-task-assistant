from fastapi import APIRouter, Depends

from mcp_assistant.api.auth.dependencies import require_auth
from mcp_assistant.api.models.auth import UserInfo

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])
