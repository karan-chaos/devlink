import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_database
from app.models.project import Project
from app.models.user import User
from app.schemas.project_dependency import (
    DependencyCreate,
    DependencyUpdate,
    DependencyResponse,
    DependencyListResponse,
    DependencyAuditSummary,
    DependencyBulkImport,
    VersionLogResponse,
)
from app.services.project_dependency_service import DependencyService

router = APIRouter(prefix="/project-dependencies", tags=["Project Dependencies"])


@router.post(
    "/project/{project_id}",
    response_model=DependencyResponse,
    status_code=201,
    summary="Add a dependency to a project",
)
def add_dependency(
    project_id: uuid.UUID,
    body: DependencyCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return DependencyService.create(db, project_id, current_user.id, body)


@router.get(
    "/project/{project_id}",
    response_model=DependencyListResponse,
    summary="List dependencies for a project",
)
def list_dependencies(
    project_id: uuid.UUID,
    category: Optional[str] = Query(None, max_length=50),
    search: Optional[str] = Query(None, max_length=200),
    critical_only: bool = Query(False),
    outdated_only: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_database),
):
    return DependencyService.list_dependencies(
        db,
        project_id,
        category=category,
        search=search,
        critical_only=critical_only,
        outdated_only=outdated_only,
        page=page,
        limit=limit,
    )


@router.post(
    "/project/{project_id}/bulk-import",
    summary="Bulk import dependencies into a project",
)
def bulk_import(
    project_id: uuid.UUID,
    body: DependencyBulkImport,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return DependencyService.bulk_import(db, project_id, current_user.id, body)


@router.get(
    "/project/{project_id}/audit",
    response_model=DependencyAuditSummary,
    summary="Get dependency audit summary for a project",
)
def audit_summary(
    project_id: uuid.UUID,
    db: Session = Depends(get_database),
):
    return DependencyService.get_audit_summary(db, project_id)


@router.get(
    "/{dep_id}",
    response_model=DependencyResponse,
    summary="Get a single dependency",
)
def get_dependency(
    dep_id: str,
    db: Session = Depends(get_database),
):
    dep = DependencyService.get(db, dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    return dep


@router.patch(
    "/{dep_id}",
    response_model=DependencyResponse,
    summary="Update a dependency",
)
def update_dependency(
    dep_id: str,
    body: DependencyUpdate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    dep = DependencyService.update(db, dep_id, current_user.id, body)
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    return dep


@router.delete(
    "/{dep_id}",
    status_code=204,
    summary="Remove a dependency from a project",
)
def delete_dependency(
    dep_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    if not DependencyService.delete(db, dep_id):
        raise HTTPException(status_code=404, detail="Dependency not found")


@router.get(
    "/{dep_id}/version-history",
    response_model=list[VersionLogResponse],
    summary="Get version change history for a dependency",
)
def version_history(
    dep_id: str,
    db: Session = Depends(get_database),
):
    dep = DependencyService.get(db, dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
    return DependencyService.get_version_history(db, dep_id)
