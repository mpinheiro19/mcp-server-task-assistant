from pydantic import BaseModel


class CreatePrdRequest(BaseModel):
    feature_name: str
    content: str


class CreateSpecRequest(BaseModel):
    feature_name: str
    prd_filename: str
    content: str


class CreatePlanRequest(BaseModel):
    feature_name: str
    content: str


class ArtifactCreatedResponse(BaseModel):
    filename: str
    path: str


class ArtifactEntry(BaseModel):
    filename: str
    size_bytes: int
    modified_at: str
    type: str | None = None


class ListArtifactsResponse(BaseModel):
    items: list[ArtifactEntry]
    total: int
