from fastapi import APIRouter, HTTPException

from mcp_assistant.api.models.artifacts import (
    ArtifactCreatedResponse,
    ArtifactEntry,
    CreatePlanRequest,
    CreatePrdRequest,
    CreateSpecRequest,
    ListArtifactsResponse,
)
from mcp_assistant.tools.artifacts import create_plan, create_prd, create_spec
from mcp_assistant.tools.workflow import list_artefacts

router = APIRouter(tags=["artifacts"])


@router.post("/artifacts/prds", response_model=ArtifactCreatedResponse, status_code=201)
async def api_create_prd(body: CreatePrdRequest) -> ArtifactCreatedResponse:
    try:
        result = create_prd(body.feature_name, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ArtifactCreatedResponse(**result)


@router.post("/artifacts/specs", response_model=ArtifactCreatedResponse, status_code=201)
async def api_create_spec(body: CreateSpecRequest) -> ArtifactCreatedResponse:
    try:
        result = create_spec(body.feature_name, body.prd_filename, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ArtifactCreatedResponse(**result)


@router.post("/artifacts/plans", response_model=ArtifactCreatedResponse, status_code=201)
async def api_create_plan(body: CreatePlanRequest) -> ArtifactCreatedResponse:
    try:
        result = create_plan(body.feature_name, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ArtifactCreatedResponse(**result)


@router.get("/artifacts", response_model=ListArtifactsResponse)
async def api_list_artifacts(type: str = "all") -> ListArtifactsResponse:
    try:
        raw = list_artefacts(type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    items = [ArtifactEntry(**entry) for entry in raw]
    return ListArtifactsResponse(items=items, total=len(items))
