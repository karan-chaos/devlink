import uuid
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class StreakRecordCreate(BaseModel):
    activity_date: date
    activity_type: str = Field(default="general", max_length=50)


class StreakRecordResponse(BaseModel):
    id: str
    user_id: uuid.UUID
    project_id: uuid.UUID
    activity_date: date
    activity_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class StreakSummaryResponse(BaseModel):
    user_id: uuid.UUID
    project_id: uuid.UUID
    current_streak: int
    longest_streak: int
    last_active_date: Optional[date] = None
    total_active_days: int

    class Config:
        from_attributes = True


class StreakLeaderboardEntry(BaseModel):
    rank: int
    user_id: uuid.UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    current_streak: int
    longest_streak: int
    total_active_days: int


class StreakLeaderboardResponse(BaseModel):
    project_id: uuid.UUID
    entries: List[StreakLeaderboardEntry]
    total_participants: int


class StreakHeatmapDay(BaseModel):
    date: date
    count: int


class StreakHeatmapResponse(BaseModel):
    user_id: uuid.UUID
    project_id: uuid.UUID
    year: int
    weeks: List[List[Optional[StreakHeatmapDay]]]


class StreakBulkLogRequest(BaseModel):
    dates: List[date] = Field(..., min_length=1, max_length=90)
    activity_type: str = Field(default="general", max_length=50)


class StreakProjectStatsResponse(BaseModel):
    project_id: uuid.UUID
    total_active_users: int
    average_streak: float
    longest_current_streak: int
    active_last_7_days: int
    active_last_30_days: int
