"""
Orchestrates the full upload pipeline: Parse -> Normalize -> Categorize ->
Detect -> Persist (per plan section 6).
"""

import uuid

import pandas as pd
from sqlalchemy.orm import Session

from app.categorizer import categorize_merchant
from app.detectors.category_drift import detect_category_drift
from app.detectors.dormant_subscription import detect_dormant_subscriptions
from app.detectors.duplicate import detect_duplicates
from app.detectors.price_creep import detect_price_creep
from app.models import AnomalyType, DetectedAnomaly, Severity, Transaction, Upload, UploadStatus
from app.normalizer import normalize_merchant
from app.parser import parse_csv

DETECTOR_FUNCS = [
    ("duplicate_charge", detect_duplicates),
    ("dormant_subscription", detect_dormant_subscriptions),
    ("price_creep", detect_price_creep),
    ("category_drift", detect_category_drift),
]


def process_upload(file_content: bytes, filename: str, user_id: uuid.UUID, db: Session) -> Upload:
    upload = Upload(user_id=user_id, filename=filename, status=UploadStatus.PROCESSING)
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        parse_result = parse_csv(file_content)

        if parse_result.transactions.empty:
            upload.status = UploadStatus.FAILED
            db.commit()
            return upload

        transactions_orm: list[Transaction] = []
        for _, row in parse_result.transactions.iterrows():
            normalized = normalize_merchant(row["description"])
            category, source = categorize_merchant(normalized, db)

            txn = Transaction(
                user_id=user_id,
                upload_id=upload.id,
                date=row["datetime"],
                merchant=row["description"],
                normalized_merchant=normalized,
                amount=row["amount"],
                category=category,
                category_source=source,
            )
            db.add(txn)
            transactions_orm.append(txn)

        db.commit()
        for txn in transactions_orm:
            db.refresh(txn)

        detector_df = pd.DataFrame({
            "normalized_merchant": [t.normalized_merchant for t in transactions_orm],
            "amount": [float(t.amount) for t in transactions_orm],
            "datetime": [t.date for t in transactions_orm],
            "category": [t.category for t in transactions_orm],
        })

        for type_str, detector_fn in DETECTOR_FUNCS:
            findings = detector_fn(detector_df)
            for anomaly in findings:
                linked_txn_ids = [transactions_orm[i].id for i in anomaly.transaction_indices]
                db.add(DetectedAnomaly(
                    user_id=user_id,
                    upload_id=upload.id,
                    transaction_id=linked_txn_ids[0] if linked_txn_ids else None,
                    type=AnomalyType(type_str),
                    reason=anomaly.reason,
                    evidence=anomaly.evidence,
                    severity=Severity(anomaly.severity),
                ))

        db.commit()

        upload.status = UploadStatus.COMPLETED
        db.commit()
        db.refresh(upload)
        return upload

    except Exception:
        upload.status = UploadStatus.FAILED
        db.commit()
        raise