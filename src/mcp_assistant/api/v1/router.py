from fastapi import APIRouter, Depends

from mcp_assistant.api.auth.dependencies import require_auth

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])
