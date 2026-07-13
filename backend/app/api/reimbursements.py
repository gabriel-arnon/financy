from fastapi import APIRouter, Depends, Request

from app.api.deps import get_file_service, get_reimbursement_service, get_request_user, get_request_user_id
from app.core.auth import CurrentUser
from app.schemas.files import FileSignedUrlRead
from app.schemas.reimbursements import (
    GuestReimbursementAction,
    GuestReimbursementClaimRead,
    ReimbursementClaimCreate,
    ReimbursementClaimAttachmentCreate,
    ReimbursementClaimAttachmentRead,
    ReimbursementClaimRead,
    ReimbursementClaimUpdate,
    ReimbursementContactCreate,
    ReimbursementContactRead,
    ReimbursementContactUpdate,
    ReimbursementEligibleTransactionRead,
    ReimbursementEventRead,
    ReimbursementInvitationAccept,
    ReimbursementInvitationCreate,
    ReimbursementInvitationCreatedRead,
    ReimbursementInvitationRead,
    ReimbursementItemCreate,
    ReimbursementItemUpdate,
    ReimbursementMembershipRead,
    ReimbursementOverviewRead,
)
from app.services.reimbursement_service import ReimbursementService
from app.services.file_storage_service import FileService


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


@router.get("/invitations", response_model=list[ReimbursementInvitationRead])
def list_invitations(
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementInvitationRead]:
    return service.list_invitations(user_id=user_id)


@router.post("/invitations", response_model=ReimbursementInvitationCreatedRead)
def create_invitation(
    payload: ReimbursementInvitationCreate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementInvitationCreatedRead:
    return service.create_invitation(user_id=user_id, payload=payload)


@router.post("/invitations/{invitation_id}/revoke", response_model=ReimbursementInvitationRead)
def revoke_invitation(
    invitation_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementInvitationRead:
    return service.revoke_invitation(user_id=user_id, invitation_id=invitation_id)


@router.get("/memberships", response_model=list[ReimbursementMembershipRead])
def list_memberships(
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementMembershipRead]:
    return service.list_memberships(user_id=user_id)


@router.post("/memberships/{membership_id}/revoke", response_model=ReimbursementMembershipRead)
def revoke_membership(
    membership_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementMembershipRead:
    return service.revoke_membership(user_id=user_id, membership_id=membership_id)


@router.post("/guest/invitations/accept", response_model=ReimbursementMembershipRead)
def accept_guest_invitation(
    payload: ReimbursementInvitationAccept,
    user: CurrentUser = Depends(get_request_user),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementMembershipRead:
    return service.accept_invitation(user=user, payload=payload)


@router.get("/guest/claims", response_model=list[GuestReimbursementClaimRead])
def list_guest_claims(
    user: CurrentUser = Depends(get_request_user),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[GuestReimbursementClaimRead]:
    return service.list_guest_claims(guest_user_id=user.id)


@router.get("/guest/claims/{claim_id}", response_model=GuestReimbursementClaimRead)
def get_guest_claim(
    claim_id: str,
    user: CurrentUser = Depends(get_request_user),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> GuestReimbursementClaimRead:
    return service.get_guest_claim(guest_user_id=user.id, claim_id=claim_id)


@router.post("/guest/claims/{claim_id}/acknowledge", response_model=GuestReimbursementClaimRead)
def acknowledge_guest_claim(
    claim_id: str,
    user: CurrentUser = Depends(get_request_user),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> GuestReimbursementClaimRead:
    return service.acknowledge_guest_claim(guest_user_id=user.id, claim_id=claim_id)


@router.post("/guest/claims/{claim_id}/dispute", response_model=GuestReimbursementClaimRead)
def dispute_guest_claim(
    claim_id: str,
    payload: GuestReimbursementAction,
    user: CurrentUser = Depends(get_request_user),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> GuestReimbursementClaimRead:
    return service.dispute_guest_claim(guest_user_id=user.id, claim_id=claim_id, payload=payload)


@router.post("/claims/{claim_id}/attachments", response_model=ReimbursementClaimAttachmentRead)
def add_claim_attachment(
    claim_id: str,
    payload: ReimbursementClaimAttachmentCreate,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> ReimbursementClaimAttachmentRead:
    return service.add_claim_attachment(user_id=user_id, claim_id=claim_id, payload=payload)


@router.get("/claims/{claim_id}/attachments", response_model=list[ReimbursementClaimAttachmentRead])
def list_claim_attachments(
    claim_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementClaimAttachmentRead]:
    return service.list_claim_attachments(user_id=user_id, claim_id=claim_id)


@router.delete("/claims/{claim_id}/attachments/{attachment_id}", response_model=dict[str, str])
def remove_claim_attachment(
    claim_id: str,
    attachment_id: str,
    user_id: str = Depends(get_request_user_id),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> dict[str, str]:
    return service.remove_claim_attachment(user_id=user_id, claim_id=claim_id, attachment_id=attachment_id)


@router.get("/guest/claims/{claim_id}/attachments", response_model=list[ReimbursementClaimAttachmentRead])
def list_guest_claim_attachments(
    claim_id: str,
    user: CurrentUser = Depends(get_request_user),
    service: ReimbursementService = Depends(get_reimbursement_service),
) -> list[ReimbursementClaimAttachmentRead]:
    return service.list_guest_claim_attachments(guest_user_id=user.id, claim_id=claim_id)


@router.get("/guest/claims/{claim_id}/attachments/{attachment_id}/signed-url", response_model=FileSignedUrlRead)
def get_guest_claim_attachment_signed_url(
    claim_id: str,
    attachment_id: str,
    request: Request,
    user: CurrentUser = Depends(get_request_user),
    service: ReimbursementService = Depends(get_reimbursement_service),
    file_service: FileService = Depends(get_file_service),
) -> FileSignedUrlRead:
    owner_user_id, file_id = service.guest_claim_attachment_file(guest_user_id=user.id, claim_id=claim_id, attachment_id=attachment_id)
    return file_service.signed_url(user_id=owner_user_id, file_id=file_id, base_url=str(request.base_url).rstrip("/"))
