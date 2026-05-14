from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from model import AuditLog
from schema import AuditLogOut
from dependencies import require_admin
from cache import cache_info
from monitoring import get_metrics

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    return db.query(AuditLog).all()


@router.get("/dashboard")
def get_monitoring_dashboard(
    current_user: dict = Depends(require_admin)
):
    return {
        "system_health": "healthy",
        "metrics": get_metrics(),
        "cache": cache_info(),
    }


@router.get("/metrics")
def get_application_metrics(
    current_user: dict = Depends(require_admin)
):
    return get_metrics()


@router.get("/cache")
def get_cache_status(
    current_user: dict = Depends(require_admin)
):
    return cache_info()
