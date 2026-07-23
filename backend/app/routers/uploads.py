from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_owned_profile
from ..importer import import_workbook
from ..models import Profile

router = APIRouter(prefix="/api/profiles", tags=["uploads"])

_ALLOWED = (".xlsx", ".xlsm")


@router.post("/{profile_id}/upload")
async def upload_workbook(
    file: UploadFile = File(...),
    profile: Profile = Depends(get_owned_profile),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(_ALLOWED):
        raise HTTPException(status_code=422, detail="Please upload an .xlsx / .xlsm file")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    try:
        result = import_workbook(db, profile, content)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"Failed to parse workbook: {exc}")
    return {"filename": file.filename, **result}
