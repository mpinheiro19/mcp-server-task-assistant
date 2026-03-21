import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mcp_assistant.api.auth.router import router as auth_router
from mcp_assistant.api.models.common import ErrorResponse, HealthResponse
from mcp_assistant.api.v1.artifacts import router as artifacts_router
from mcp_assistant.api.v1.resources import router as resources_router
from mcp_assistant.api.v1.router import router as v1_router
from mcp_assistant.api.v1.workflow import router as workflow_router


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            detail=str(exc),
            status_code=500,
        ).model_dump(),
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="MCP Assistant REST API",
        version="1.0.0-beta.2",
        description="REST API layer for the MCP Assistant artifact lifecycle operations.",
    )

    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(Exception, global_exception_handler)

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    app.include_router(auth_router)

    # Mount v1 sub-routers under the protected v1 router
    v1_router.include_router(artifacts_router)
    v1_router.include_router(workflow_router)
    v1_router.include_router(resources_router)
    app.include_router(v1_router)

    return app
