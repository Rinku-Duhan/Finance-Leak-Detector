from fastapi import APIRouter

from app.categorizer import VALID_CATEGORIES

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/")
def list_categories():
    return {"categories": VALID_CATEGORIES}