import math
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.project_dependency import ProjectDependency, DependencyVersionLog
from app.schemas.project_dependency import (
    DependencyCreate,
    DependencyUpdate,
    DependencyBulkImport,
)


class DependencyService:

    @staticmethod
    def create(
        db: Session,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: DependencyCreate,
    ) -> ProjectDependency:
        dep = ProjectDependency(
            project_id=project_id,
            added_by_id=user_id,
            name=payload.name,
            current_version=payload.current_version,
            latest_version=payload.latest_version,
            category=payload.category,
            description=payload.description,
            homepage_url=payload.homepage_url,
            is_critical=payload.is_critical,
        )
        db.add(dep)
        db.commit()
        db.refresh(dep)
        return dep

    @staticmethod
    def get(db: Session, dep_id: str) -> Optional[ProjectDependency]:
        return db.query(ProjectDependency).filter(ProjectDependency.id == dep_id).first()

    @staticmethod
    def list_dependencies(
        db: Session,
        project_id: uuid.UUID,
        *,
        category: Optional[str] = None,
        search: Optional[str] = None,
        critical_only: bool = False,
        outdated_only: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        query = db.query(ProjectDependency).filter(
            ProjectDependency.project_id == project_id
        )
        if category:
            query = query.filter(ProjectDependency.category == category)
        if search:
            query = query.filter(
                or_(
                    ProjectDependency.name.ilike(f"%{search}%"),
                    ProjectDependency.description.ilike(f"%{search}%"),
                )
            )
        if critical_only:
            query = query.filter(ProjectDependency.is_critical == True)
        if outdated_only:
            query = query.filter(ProjectDependency.is_outdated == True)

        total = query.count()
        items = (
            query.order_by(
                ProjectDependency.is_critical.desc(),
                ProjectDependency.name,
            )
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, math.ceil(total / limit)),
        }

    @staticmethod
    def update(
        db: Session,
        dep_id: str,
        user_id: uuid.UUID,
        payload: DependencyUpdate,
    ) -> Optional[ProjectDependency]:
        dep = db.query(ProjectDependency).filter(ProjectDependency.id == dep_id).first()
        if not dep:
            return None

        old_version = dep.current_version
        updates = payload.model_dump(exclude_unset=True)

        # Track version changes in history log
        if "current_version" in updates and updates["current_version"] != old_version:
            log = DependencyVersionLog(
                dependency_id=dep.id,
                old_version=old_version,
                new_version=updates["current_version"],
                changed_by_id=user_id,
            )
            db.add(log)

        for field, value in updates.items():
            setattr(dep, field, value)

        # Auto-detect outdated status
        if dep.current_version and dep.latest_version:
            dep.is_outdated = dep.current_version != dep.latest_version

        db.commit()
        db.refresh(dep)
        return dep

    @staticmethod
    def delete(db: Session, dep_id: str) -> bool:
        dep = db.query(ProjectDependency).filter(ProjectDependency.id == dep_id).first()
        if not dep:
            return False
        db.delete(dep)
        db.commit()
        return True

    @staticmethod
    def bulk_import(
        db: Session,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: DependencyBulkImport,
    ) -> dict:
        created = 0
        skipped = 0
        for dep_data in payload.dependencies:
            existing = (
                db.query(ProjectDependency)
                .filter(
                    ProjectDependency.project_id == project_id,
                    ProjectDependency.name == dep_data.name,
                )
                .first()
            )
            if existing:
                skipped += 1
                continue
            dep = ProjectDependency(
                project_id=project_id,
                added_by_id=user_id,
                name=dep_data.name,
                current_version=dep_data.current_version,
                latest_version=dep_data.latest_version,
                category=dep_data.category,
                description=dep_data.description,
                homepage_url=dep_data.homepage_url,
                is_critical=dep_data.is_critical,
            )
            db.add(dep)
            created += 1
        db.commit()
        return {"created": created, "skipped": skipped, "total": len(payload.dependencies)}

    @staticmethod
    def get_version_history(db: Session, dep_id: str) -> List[DependencyVersionLog]:
        return (
            db.query(DependencyVersionLog)
            .filter(DependencyVersionLog.dependency_id == dep_id)
            .order_by(DependencyVersionLog.changed_at.desc())
            .all()
        )

    @staticmethod
    def get_audit_summary(db: Session, project_id: uuid.UUID) -> dict:
        deps = (
            db.query(ProjectDependency)
            .filter(ProjectDependency.project_id == project_id)
            .all()
        )

        total = len(deps)
        critical = sum(1 for d in deps if d.is_critical)
        outdated = sum(1 for d in deps if d.is_outdated)
        up_to_date = total - outdated

        by_category = {}
        for d in deps:
            by_category[d.category] = by_category.get(d.category, 0) + 1

        # Health score: 100 is perfect, each outdated dep loses 5pts, each critical+outdated loses 10pts
        if total == 0:
            health_score = 100.0
        else:
            deductions = 0
            for d in deps:
                if d.is_outdated and d.is_critical:
                    deductions += 10
                elif d.is_outdated:
                    deductions += 5
            health_score = max(0.0, 100.0 - (deductions / total * 100))

        return {
            "project_id": project_id,
            "total_dependencies": total,
            "critical_count": critical,
            "outdated_count": outdated,
            "up_to_date_count": up_to_date,
            "by_category": by_category,
            "health_score": round(health_score, 1),
        }
