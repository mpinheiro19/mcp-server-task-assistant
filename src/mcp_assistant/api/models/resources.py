from pydantic import BaseModel


class ResourceListResponse(BaseModel):
    items: list[str]
    total: int


class ResourceFileResponse(BaseModel):
    filename: str
    content: str


class IndexResponse(BaseModel):
    content: str


class ProjectsResponse(BaseModel):
    projects: list[str]
