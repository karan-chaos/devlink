import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


VALID_CATEGORIES = ("frontend", "backend", "database", "devops", "testing", "utility", "other")


class DependencyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    current_version: Optional[str] = Field(default=None, max_length=50)
    latest_version: Optional[str] = Field(default=None, max_length=50)
    category: str = Field(default="other", max_length=50)
    description: Optional[str] = None
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    is_critical: bool = False


class DependencyUpdate(BaseModel):
    current_version: Optional[str] = Field(default=None, max_length=50)
    latest_version: Optional[str] = Field(default=None, max_length=50)
    category: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    homepage_url: Optional[str] = Field(default=None, max_length=500)
    is_critical: Optional[bool] = None


class DependencyResponse(BaseModel):
    id: str
    project_id: uuid.UUID
    added_by_id: uuid.UUID
    name: str
    current_version: Optional[str] = None
    latest_version: Optional[str] = None
    category: str
    description: Optional[str] = None
    homepage_url: Optional[str] = None
    is_critical: bool
    is_outdated: bool
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DependencyBrief(BaseModel):
    id: str
    name: str
    current_version: Optional[str] = None
    category: str
    is_critical: bool
    is_outdated: bool

    class Config:
        from_attributes = True


class VersionLogResponse(BaseModel):
    id: str
    dependency_id: str
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    changed_by_id: Optional[uuid.UUID] = None
    changed_at: datetime

    class Config:
        from_attributes = True


class DependencyListResponse(BaseModel):
    items: List[DependencyResponse]
    total: int
    page: int
    limit: int
    pages: int


class DependencyAuditSummary(BaseModel):
    project_id: uuid.UUID
    total_dependencies: int
    critical_count: int
    outdated_count: int
    up_to_date_count: int
    by_category: dict
    health_score: float  # 0-100, higher is healthier


class DependencyBulkImport(BaseModel):
    dependencies: List[DependencyCreate] = Field(..., min_length=1, max_length=100)
