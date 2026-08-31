import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_database
from app.models.project import Project
from app.models.user import User
from app.schemas.streak import (
    StreakRecordResponse,
    StreakSummaryResponse,
    StreakLeaderboardResponse,
    StreakHeatmapResponse,
    StreakHeatmapDay,
    StreakBulkLogRequest,
    StreakProjectStatsResponse,
)
from app.services.streak_service import StreakService

router = APIRouter(prefix="/streaks", tags=["Developer Streaks"])


@router.post(
    "/project/{project_id}/record",
    response_model=StreakRecordResponse,
    status_code=201,
    summary="Record a day of activity",
)
def record_activity(
    project_id: uuid.UUID,
    body: StreakRecordCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    record = StreakService.record_activity(
        db, current_user.id, project_id, body.activity_date
    )
    return record


@router.post(
    "/project/{project_id}/bulk-record",
    summary="Record multiple activity days at once",
)
def bulk_record(
    project_id: uuid.UUID,
    body: StreakBulkLogRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    count = StreakService.bulk_record(
        db, current_user.id, project_id, body.dates, body.activity_type
    )
    return {"recorded": count, "total_dates": len(body.dates)}


@router.get(
    "/project/{project_id}/me",
    response_model=StreakSummaryResponse,
    summary="Get my streak summary for a project",
)
def my_streak(
    project_id: uuid.UUID,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return StreakService.get_summary(db, current_user.id, project_id)


@router.get(
    "/project/{project_id}/user/{user_id}",
    response_model=StreakSummaryResponse,
    summary="Get a user's streak summary for a project",
)
def user_streak(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_database),
):
    return StreakService.get_summary(db, user_id, project_id)


@router.get(
    "/project/{project_id}/leaderboard",
    response_model=StreakLeaderboardResponse,
    summary="Get the streak leaderboard for a project",
)
def leaderboard(
    project_id: uuid.UUID,
    sort_by: str = Query(
        "current_streak",
        regex="^(current_streak|longest_streak|total_active_days)$",
    ),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_database),
):
    return StreakService.get_leaderboard(db, project_id, sort_by=sort_by, limit=limit)


@router.get(
    "/project/{project_id}/user/{user_id}/heatmap/{year}",
    response_model=StreakHeatmapResponse,
    summary="Get a yearly activity heatmap for a user",
)
def heatmap(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    year: int,
    db: Session = Depends(get_database),
):
    days = StreakService.get_heatmap(db, user_id, project_id, year)
    # Group into weeks (7-day chunks)
    weeks = []
    for i in range(0, len(days), 7):
        weeks.append(days[i : i + 7])
    return StreakHeatmapResponse(
        user_id=user_id,
        project_id=project_id,
        year=year,
        weeks=weeks,
    )


@router.get(
    "/project/{project_id}/stats",
    response_model=StreakProjectStatsResponse,
    summary="Get streak statistics for a project",
)
def project_stats(
    project_id: uuid.UUID,
    db: Session = Depends(get_database),
):
    return StreakService.get_project_stats(db, project_id)
