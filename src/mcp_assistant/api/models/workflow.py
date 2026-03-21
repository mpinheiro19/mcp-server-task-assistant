from pydantic import BaseModel


class WorkflowSummary(BaseModel):
    done: int
    in_progress: int
    todo: int


class FeatureEntry(BaseModel):
    prd: str
    spec: str
    feature: str
    plan_status: str
    implementation: str


class WorkflowStatusResponse(BaseModel):
    features: list[FeatureEntry]
    summary: WorkflowSummary


class UpdateIndexRequest(BaseModel):
    prd_filename: str
    spec_filename: str
    feature_name: str
    plan_status: str
    implementation_status: str


class AdvanceStageRequest(BaseModel):
    plan_status: str
    implementation_status: str


class CheckDuplicateResponse(BaseModel):
    has_duplicate: bool
    matches: list[str]
