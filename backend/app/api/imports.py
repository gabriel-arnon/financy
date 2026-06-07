from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_import_service, get_user_id
from app.schemas.imports import ConfirmImportRequest, ConfirmImportResponse, ImportPreviewResponse, UploadImportResponse
from app.services.import_service import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/upload", response_model=UploadImportResponse)
async def upload_import(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id),
    service: ImportService = Depends(get_import_service),
) -> UploadImportResponse:
    return await service.upload(user_id=user_id, file=file)


@router.get("/{import_id}/preview", response_model=ImportPreviewResponse)
def get_preview(
    import_id: str,
    user_id: str = Depends(get_user_id),
    service: ImportService = Depends(get_import_service),
) -> ImportPreviewResponse:
    return service.get_preview(user_id=user_id, import_id=import_id)


@router.post("/{import_id}/confirm", response_model=ConfirmImportResponse)
def confirm_import(
    import_id: str,
    payload: ConfirmImportRequest,
    user_id: str = Depends(get_user_id),
    service: ImportService = Depends(get_import_service),
) -> ConfirmImportResponse:
    return service.confirm(user_id=user_id, import_id=import_id, payload=payload)
