from fastapi import APIRouter, HTTPException

from mcp_assistant.api.models.workflow import (
    AdvanceStageRequest,
    CheckDuplicateResponse,
    FeatureEntry,
    UpdateIndexRequest,
    WorkflowStatusResponse,
    WorkflowSummary,
)
from mcp_assistant.tools.workflow import (
    advance_stage,
    check_duplicate,
    get_workflow_status,
    update_index,
)

router = APIRouter(tags=["workflow"])


@router.get("/workflow/status", response_model=WorkflowStatusResponse)
async def api_workflow_status() -> WorkflowStatusResponse:
    result = get_workflow_status()
    return WorkflowStatusResponse(
        features=[FeatureEntry(**f) for f in result["features"]],
        summary=WorkflowSummary(**result["summary"]),
    )


@router.put("/workflow/index", response_model=dict)
async def api_update_index(body: UpdateIndexRequest) -> dict:
    try:
        content = update_index(
            body.prd_filename,
            body.spec_filename,
            body.feature_name,
            body.plan_status,
            body.implementation_status,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"content": content}


@router.patch("/workflow/features/{feature_name}/stage", response_model=dict)
async def api_advance_stage(feature_name: str, body: AdvanceStageRequest) -> dict:
    try:
        content = advance_stage(feature_name, body.plan_status, body.implementation_status)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"content": content}


@router.get("/workflow/duplicates", response_model=CheckDuplicateResponse)
async def api_check_duplicate(feature_name: str) -> CheckDuplicateResponse:
    result = check_duplicate(feature_name)
    return CheckDuplicateResponse(**result)
