from fastapi import APIRouter, Depends, Query

from app.api.deps import get_job_service, get_request_user_id
from app.schemas.jobs import JobRunRead
from app.services.job_service import JobService


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRunRead])
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_request_user_id),
    service: JobService = Depends(get_job_service),
) -> list[JobRunRead]:
    return service.list(user_id, limit=limit)


@router.get("/{job_id}", response_model=JobRunRead)
def get_job(
    job_id: str,
    user_id: str = Depends(get_request_user_id),
    service: JobService = Depends(get_job_service),
) -> JobRunRead:
    return service.get(user_id, job_id)
