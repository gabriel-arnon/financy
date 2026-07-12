from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_file_service, get_request_user_id
from app.schemas.files import FileSignedUrlRead, StoredFileRead, TransactionAttachmentCreate, TransactionAttachmentRead
from app.services.file_storage_service import FileService


files_router = APIRouter(prefix="/files", tags=["files"])
transaction_attachments_router = APIRouter(prefix="/transactions", tags=["transaction-attachments"])


@files_router.post("/upload", response_model=StoredFileRead)
async def upload_file(
    file: UploadFile = File(...),
    source: str = "manual",
    user_id: str = Depends(get_request_user_id),
    service: FileService = Depends(get_file_service),
) -> StoredFileRead:
    return await service.upload(user_id=user_id, file=file, source=source)


@files_router.get("/{file_id}/signed-url", response_model=FileSignedUrlRead)
def get_file_signed_url(
    file_id: str,
    request: Request,
    user_id: str = Depends(get_request_user_id),
    service: FileService = Depends(get_file_service),
) -> FileSignedUrlRead:
    return service.signed_url(user_id=user_id, file_id=file_id, base_url=str(request.base_url).rstrip("/"))


@files_router.delete("/{file_id}", response_model=StoredFileRead)
def delete_file(
    file_id: str,
    user_id: str = Depends(get_request_user_id),
    service: FileService = Depends(get_file_service),
) -> StoredFileRead:
    return service.delete(user_id=user_id, file_id=file_id)


@files_router.get("/{file_id}/download")
def download_file(
    file_id: str,
    expires: int,
    token: str,
    service: FileService = Depends(get_file_service),
) -> FileResponse:
    path = service.local_download_path(file_id=file_id, expires=expires, token=token)
    return FileResponse(path, filename=path.name)


@transaction_attachments_router.post("/{transaction_id}/attachments", response_model=TransactionAttachmentRead)
def attach_file_to_transaction(
    transaction_id: str,
    payload: TransactionAttachmentCreate,
    user_id: str = Depends(get_request_user_id),
    service: FileService = Depends(get_file_service),
) -> TransactionAttachmentRead:
    return service.attach_to_transaction(user_id=user_id, transaction_id=transaction_id, file_id=payload.file_id)


@transaction_attachments_router.get("/{transaction_id}/attachments", response_model=list[TransactionAttachmentRead])
def list_transaction_attachments(
    transaction_id: str,
    user_id: str = Depends(get_request_user_id),
    service: FileService = Depends(get_file_service),
) -> list[TransactionAttachmentRead]:
    return service.list_transaction_attachments(user_id=user_id, transaction_id=transaction_id)


@transaction_attachments_router.delete("/{transaction_id}/attachments/{attachment_id}", response_model=dict[str, str])
def delete_transaction_attachment(
    transaction_id: str,
    attachment_id: str,
    user_id: str = Depends(get_request_user_id),
    service: FileService = Depends(get_file_service),
) -> dict[str, str]:
    return service.delete_transaction_attachment(user_id=user_id, transaction_id=transaction_id, attachment_id=attachment_id)
