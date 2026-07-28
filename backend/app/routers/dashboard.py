from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_owned_upload
from app.models import DetectedAnomaly, Transaction, User
from app.narrative import generate_narrative
from app.schemas import AnomalyOut, DashboardSummary, NarrativeOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _build_summary(upload_id: str, db: Session) -> dict:
    txns = db.query(Transaction).filter(Transaction.upload_id == upload_id).all()

    total_spent = sum(float(t.amount) for t in txns if float(t.amount) < 0)
    total_income = sum(float(t.amount) for t in txns if float(t.amount) > 0)

    by_category: dict[str, float] = {}
    for t in txns:
        by_category.setdefault(t.category, 0.0)
        by_category[t.category] += float(t.amount)

    return {
        "upload_id": upload_id,
        "total_transactions": len(txns),
        "total_spent": round(abs(total_spent), 2),
        "total_income": round(total_income, 2),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
    }


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_upload(upload_id, db, current_user)
    return _build_summary(upload_id, db)


@router.get("/anomalies", response_model=list[AnomalyOut])
def dashboard_anomalies(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_upload(upload_id, db, current_user)

    anomalies = (
        db.query(DetectedAnomaly)
        .filter(DetectedAnomaly.upload_id == upload_id)
        .order_by(DetectedAnomaly.detected_at.desc())
        .all()
    )

    return [
        AnomalyOut(
            id=str(a.id),
            type=a.type.value,
            reason=a.reason,
            evidence=a.evidence,
            severity=a.severity.value,
            transaction_id=str(a.transaction_id) if a.transaction_id else None,
        )
        for a in anomalies
    ]


@router.get("/narrative", response_model=NarrativeOut)
def dashboard_narrative(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_upload(upload_id, db, current_user)

    summary = _build_summary(upload_id, db)
    anomalies = dashboard_anomalies(upload_id, db, current_user)
    anomaly_dicts = [a.model_dump() for a in anomalies]

    narrative_text = generate_narrative(summary, anomaly_dicts)
    return NarrativeOut(upload_id=upload_id, narrative=narrative_text)