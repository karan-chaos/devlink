import uuid
from datetime import date, timedelta, timezone
from typing import Optional, List
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.models.streak import StreakRecord, StreakSummary
from app.models.user import User
from app.schemas.streak import (
    StreakRecordCreate,
    StreakBulkLogRequest,
    StreakLeaderboardEntry,
    StreakHeatmapDay,
)


class StreakService:

    @staticmethod
    def record_activity(
        db: Session, user_id: uuid.UUID, project_id: uuid.UUID, activity_date: date
    ) -> StreakRecord:
        """Record a day of activity. Idempotent — duplicate days are ignored."""
        existing = (
            db.query(StreakRecord)
            .filter(
                StreakRecord.user_id == user_id,
                StreakRecord.project_id == project_id,
                StreakRecord.activity_date == activity_date,
            )
            .first()
        )
        if existing:
            return existing

        record = StreakRecord(
            user_id=user_id, project_id=project_id, activity_date=activity_date
        )
        db.add(record)
        db.flush()
        StreakService._update_summary(db, user_id, project_id)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def bulk_record(
        db: Session,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        dates: List[date],
        activity_type: str = "general",
    ) -> int:
        """Record multiple activity days at once. Returns count of new records."""
        new_count = 0
        for d in dates:
            existing = (
                db.query(StreakRecord)
                .filter(
                    StreakRecord.user_id == user_id,
                    StreakRecord.project_id == project_id,
                    StreakRecord.activity_date == d,
                )
                .first()
            )
            if not existing:
                db.add(
                    StreakRecord(
                        user_id=user_id,
                        project_id=project_id,
                        activity_date=d,
                        activity_type=activity_type,
                    )
                )
                new_count += 1
        if new_count > 0:
            db.flush()
            StreakService._update_summary(db, user_id, project_id)
            db.commit()
        return new_count

    @staticmethod
    def get_summary(
        db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> dict:
        summary = (
            db.query(StreakSummary)
            .filter(
                StreakSummary.user_id == user_id,
                StreakSummary.project_id == project_id,
            )
            .first()
        )
        if not summary:
            return {
                "user_id": user_id,
                "project_id": project_id,
                "current_streak": 0,
                "longest_streak": 0,
                "last_active_date": None,
                "total_active_days": 0,
            }
        return {
            "user_id": summary.user_id,
            "project_id": summary.project_id,
            "current_streak": summary.current_streak,
            "longest_streak": summary.longest_streak,
            "last_active_date": summary.last_active_date,
            "total_active_days": summary.total_active_days,
        }

    @staticmethod
    def get_leaderboard(
        db: Session,
        project_id: uuid.UUID,
        *,
        sort_by: str = "current_streak",
        limit: int = 20,
    ) -> dict:
        sort_col = {
            "current_streak": StreakSummary.current_streak.desc(),
            "longest_streak": StreakSummary.longest_streak.desc(),
            "total_active_days": StreakSummary.total_active_days.desc(),
        }.get(sort_by, StreakSummary.current_streak.desc())

        summaries = (
            db.query(StreakSummary)
            .filter(StreakSummary.project_id == project_id)
            .order_by(sort_col)
            .limit(limit)
            .all()
        )

        total = (
            db.query(func.count(StreakSummary.id))
            .filter(StreakSummary.project_id == project_id)
            .scalar()
            or 0
        )

        user_ids = [s.user_id for s in summaries]
        users = {}
        if user_ids:
            user_rows = (
                db.query(User).filter(User.id.in_(user_ids)).all()
            )
            users = {u.id: u for u in user_rows}

        entries = []
        for rank, s in enumerate(summaries, 1):
            user = users.get(s.user_id)
            entries.append(
                StreakLeaderboardEntry(
                    rank=rank,
                    user_id=s.user_id,
                    username=getattr(user, "username", None),
                    display_name=getattr(user, "display_name", None),
                    current_streak=s.current_streak,
                    longest_streak=s.longest_streak,
                    total_active_days=s.total_active_days,
                )
            )

        return {
            "project_id": project_id,
            "entries": entries,
            "total_participants": total,
        }

    @staticmethod
    def get_heatmap(
        db: Session,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        year: int,
    ) -> List[dict]:
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        records = (
            db.query(StreakRecord.activity_date, func.count(StreakRecord.id))
            .filter(
                StreakRecord.user_id == user_id,
                StreakRecord.project_id == project_id,
                StreakRecord.activity_date.between(start, end),
            )
            .group_by(StreakRecord.activity_date)
            .all()
        )
        count_map = {r[0]: r[1] for r in records}
        days = []
        current = start
        while current <= end:
            days.append(
                StreakHeatmapDay(
                    date=current, count=count_map.get(current, 0)
                )
            )
            current += timedelta(days=1)
        return days

    @staticmethod
    def get_project_stats(
        db: Session, project_id: uuid.UUID
    -> dict:
        total_users = (
            db.query(func.count(func.distinct(StreakSummary.user_id)))
            .filter(StreakSummary.project_id == project_id)
            .scalar()
            or 0
        )

        avg_streak = (
            db.query(func.avg(StreakSummary.current_streak))
            .filter(StreakSummary.project_id == project_id)
            .scalar()
            or 0.0
        )

        max_streak = (
            db.query(func.max(StreakSummary.current_streak))
            .filter(StreakSummary.project_id == project_id)
            .scalar()
            or 0
        )

        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        active_7d = (
            db.query(func.count(func.distinct(StreakRecord.user_id)))
            .filter(
                StreakRecord.project_id == project_id,
                StreakRecord.activity_date >= week_ago,
            )
            .scalar()
            or 0
        )

        active_30d = (
            db.query(func.count(func.distinct(StreakRecord.user_id)))
            .filter(
                StreakRecord.project_id == project_id,
                StreakRecord.activity_date >= month_ago,
            )
            .scalar()
            or 0
        )

        return {
            "project_id": project_id,
            "total_active_users": total_users,
            "average_streak": round(float(avg_streak), 1),
            "longest_current_streak": max_streak,
            "active_last_7_days": active_7d,
            "active_last_30_days": active_30d,
        }

    @staticmethod
    def _update_summary(
        db: Session, user_id: uuid.UUID, project_id: uuid.UUID
    ) -> None:
        summary = (
            db.query(StreakSummary)
            .filter(
                StreakSummary.user_id == user_id,
                StreakSummary.project_id == project_id,
            )
            .first()
        )

        all_dates = sorted(
            [
                r.activity_date
                for r in (
                    db.query(StreakRecord.activity_date)
                    .filter(
                        StreakRecord.user_id == user_id,
                        StreakRecord.project_id == project_id,
                    )
                    .order_by(StreakRecord.activity_date)
                    .all()
                )
            ]
        )

        total_days = len(all_dates)
        last_active = all_dates[-1] if all_dates else None

        # Calculate current streak (from last active date backwards)
        current_streak = 0
        if all_dates:
            check = all_dates[-1]
            today = date.today()
            # Allow today or yesterday to still count as current
            if (today - check).days <= 1:
                for d in reversed(all_dates):
                    if d == check:
                        current_streak += 1
                        check -= timedelta(days=1)
                    elif d == check:
                        current_streak += 1
                        check -= timedelta(days=1)
                    else:
                        break

        # Calculate longest streak
        longest_streak = 0
        if all_dates:
            streak = 1
            for i in range(1, len(all_dates)):
                if (all_dates[i] - all_dates[i - 1]).days == 1:
                    streak += 1
                else:
                    longest_streak = max(longest_streak, streak)
                    streak = 1
            longest_streak = max(longest_streak, streak)

        if summary:
            summary.current_streak = current_streak
            summary.longest_streak = max(summary.longest_streak, longest_streak)
            summary.last_active_date = last_active
            summary.total_active_days = total_days
        else:
            summary = StreakSummary(
                user_id=user_id,
                project_id=project_id,
                current_streak=current_streak,
                longest_streak=longest_streak,
                last_active_date=last_active,
                total_active_days=total_days,
            )
            db.add(summary)
