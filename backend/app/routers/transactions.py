from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Transaction, Upload, UploadStatus, User
from app.pipeline import process_upload
from app.schemas import TransactionOut, UploadOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/upload", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def upload_transactions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are supported")

    content = await file.read()

    try:
        upload = process_upload(content, file.filename, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if upload.status == UploadStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not parse any valid transactions from this file. Check the column format.",
        )

    return upload


@router.get("/", response_model=list[TransactionOut])
def list_transactions(
    upload_id: Optional[str] = None,
    category: Optional[str] = None,
    month: Optional[str] = Query(None, description="Filter by month, format YYYY-MM"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

    if upload_id:
        query = query.filter(Transaction.upload_id == upload_id)
    if category:
        query = query.filter(Transaction.category == category)
    if month:
        try:
            year, mon = (int(x) for x in month.split("-"))
        except ValueError:
            raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")
        query = query.filter(extract("year", Transaction.date) == year, extract("month", Transaction.date) == mon)

    query = query.order_by(Transaction.date.desc())
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    return results