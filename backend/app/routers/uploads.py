from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Upload, User
from app.schemas import UploadOut

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("/", response_model=list[UploadOut])
def list_uploads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Upload)
        .filter(Upload.user_id == current_user.id)
        .order_by(Upload.uploaded_at.desc())
        .all()
    )