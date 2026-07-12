from fastapi import APIRouter, Depends

from app.api.deps import get_reimbursement_service, get_request_user_id
from app.schemas.reimbursements import (
    ReimbursementClaimCreate,
    ReimbursementClaimRead,
    ReimbursementClaimUpdate,
    ReimbursementContactCreate,
    ReimbursementContactRead,
    ReimbursementContactUpdate,
    ReimbursementEligibleTransactionRead,
    ReimbursementEventRead,
    ReimbursementItemCreate,
    ReimbursementItemUpdate,
    ReimbursementOverviewRead,
)
from app.services.reimbursement_service import ReimbursementService


router = APIRouter(prefix="/reimbursements", tags=["reimbursements"])


@router.get("/overview", response_model=ReimbursementOverviewRead)
def get_overview(
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementOverviewRead:
    return service.overview(user_id=user_id)


@router.get("/eligible-transactions", response_model=list[ReimbursementEligibleTransactionRead])
def list_eligible_transactions(
    q: str | None = None,
    limit: int = 30,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementEligibleTransactionRead]:
    return service.list_eligible_transactions(user_id=user_id, query=q, limit=limit)


@router.get("/contacts", response_model=list[ReimbursementContactRead])
def list_contacts(
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementContactRead]:
    return service.list_contacts(user_id=user_id)


@router.post("/contacts", response_model=ReimbursementContactRead)
def create_contact(
    payload: ReimbursementContactCreate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementContactRead:
    return service.create_contact(user_id=user_id, payload=payload)


@router.patch("/contacts/{contact_id}", response_model=ReimbursementContactRead)
def update_contact(
    contact_id: str,
    payload: ReimbursementContactUpdate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementContactRead:
    return service.update_contact(user_id=user_id, contact_id=contact_id, payload=payload)


@router.delete("/contacts/{contact_id}", response_model=ReimbursementContactRead)
def delete_contact(
    contact_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementContactRead:
    return service.delete_contact(user_id=user_id, contact_id=contact_id)


@router.get("/claims", response_model=list[ReimbursementClaimRead])
def list_claims(
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementClaimRead]:
    return service.list_claims(user_id=user_id)


@router.post("/claims", response_model=ReimbursementClaimRead)
def create_claim(
    payload: ReimbursementClaimCreate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.create_claim(user_id=user_id, payload=payload)


@router.get("/claims/{claim_id}", response_model=ReimbursementClaimRead)
def get_claim(
    claim_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.get_claim(user_id=user_id, claim_id=claim_id)


@router.patch("/claims/{claim_id}", response_model=ReimbursementClaimRead)
def update_claim(
    claim_id: str,
    payload: ReimbursementClaimUpdate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.update_claim(user_id=user_id, claim_id=claim_id, payload=payload)


@router.post("/claims/{claim_id}/send", response_model=ReimbursementClaimRead)
def send_claim(
    claim_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.send_claim(user_id=user_id, claim_id=claim_id)


@router.post("/claims/{claim_id}/cancel", response_model=ReimbursementClaimRead)
def cancel_claim(
    claim_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.cancel_claim(user_id=user_id, claim_id=claim_id)


@router.post("/claims/{claim_id}/refresh-snapshots", response_model=ReimbursementClaimRead)
def refresh_claim_snapshots(
    claim_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.refresh_claim_snapshots(user_id=user_id, claim_id=claim_id)


@router.get("/claims/{claim_id}/events", response_model=list[ReimbursementEventRead])
def list_claim_events(
    claim_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementEventRead]:
    return service.list_events(user_id=user_id, claim_id=claim_id)


@router.post("/claims/{claim_id}/items", response_model=ReimbursementClaimRead)
def add_item(
    claim_id: str,
    payload: ReimbursementItemCreate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.add_item(user_id=user_id, claim_id=claim_id, payload=payload)


@router.patch("/claims/{claim_id}/items/{item_id}", response_model=ReimbursementClaimRead)
def update_item(
    claim_id: str,
    item_id: str,
    payload: ReimbursementItemUpdate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.update_item(user_id=user_id, claim_id=claim_id, item_id=item_id, payload=payload)


@router.delete("/claims/{claim_id}/items/{item_id}", response_model=ReimbursementClaimRead)
def remove_item(
    claim_id: str,
    item_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimRead:
    return service.remove_item(user_id=user_id, claim_id=claim_id, item_id=item_id)
