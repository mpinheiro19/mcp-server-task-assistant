import json

from fastapi import APIRouter, HTTPException

from mcp_assistant.api.models.resources import (
    IndexResponse,
    ProjectsResponse,
    ResourceFileResponse,
    ResourceListResponse,
)
from mcp_assistant.resources.flow import (
    get_index,
    get_plan,
    get_plans,
    get_prd,
    get_prds,
    get_projects,
    get_spec,
    get_specs,
)

router = APIRouter(tags=["resources"])


@router.get("/resources/index", response_model=IndexResponse)
async def api_get_index() -> IndexResponse:
    return IndexResponse(content=get_index())


@router.get("/resources/projects", response_model=ProjectsResponse)
async def api_get_projects() -> ProjectsResponse:
    projects = json.loads(get_projects())
    return ProjectsResponse(projects=projects)


@router.get("/resources/prds", response_model=ResourceListResponse)
async def api_get_prds() -> ResourceListResponse:
    items = json.loads(get_prds())
    return ResourceListResponse(items=items, total=len(items))


@router.get("/resources/specs", response_model=ResourceListResponse)
async def api_get_specs() -> ResourceListResponse:
    items = json.loads(get_specs())
    return ResourceListResponse(items=items, total=len(items))


@router.get("/resources/plans", response_model=ResourceListResponse)
async def api_get_plans() -> ResourceListResponse:
    items = json.loads(get_plans())
    return ResourceListResponse(items=items, total=len(items))


@router.get("/resources/prds/{filename}", response_model=ResourceFileResponse)
async def api_get_prd(filename: str) -> ResourceFileResponse:
    try:
        content = get_prd(filename)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResourceFileResponse(filename=filename, content=content)


@router.get("/resources/specs/{filename}", response_model=ResourceFileResponse)
async def api_get_spec(filename: str) -> ResourceFileResponse:
    try:
        content = get_spec(filename)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResourceFileResponse(filename=filename, content=content)


@router.get("/resources/plans/{filename}", response_model=ResourceFileResponse)
async def api_get_plan(filename: str) -> ResourceFileResponse:
    try:
        content = get_plan(filename)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ResourceFileResponse(filename=filename, content=content)
