from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.core.errors import AppError
from app.models.enums import (
    ReimbursementCommentAuthorRole,
    ReimbursementClaimStatus,
    ReimbursementInvitationStatus,
    ReimbursementItemStatus,
    ReimbursementMembershipStatus,
    TransactionType,
)
from app.schemas.reimbursements import (
    GuestReimbursementAction,
    GuestReimbursementClaimRead,
    GuestReimbursementItemRead,
    ReimbursementClaimCreate,
    ReimbursementClaimRead,
    ReimbursementClaimUpdate,
    ReimbursementCommentCreate,
    ReimbursementCommentRead,
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
    ReimbursementItemRead,
    ReimbursementItemUpdate,
    ReimbursementClaimAttachmentCreate,
    ReimbursementClaimAttachmentRead,
    ReimbursementClaimAttachmentFileRead,
    ReimbursementMembershipRead,
    ReimbursementOverviewRead,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


GUEST_SHARED_CLAIM_STATUSES = {
    ReimbursementClaimStatus.sent.value,
    ReimbursementClaimStatus.acknowledged.value,
    ReimbursementClaimStatus.disputed.value,
    ReimbursementClaimStatus.partially_paid.value,
    ReimbursementClaimStatus.paid.value,
    ReimbursementClaimStatus.canceled.value,
}


class ReimbursementService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def list_contacts(self, user_id: str) -> list[ReimbursementContactRead]:
        return [ReimbursementContactRead(**item) for item in self.repository.list_reimbursement_contacts(user_id)]

    def create_contact(self, user_id: str, payload: ReimbursementContactCreate) -> ReimbursementContactRead:
        display_name = payload.display_name.strip()
        if not display_name:
            raise AppError("Nome do contato e obrigatorio.", code="contact_name_required")
        for contact in self.repository.list_reimbursement_contacts(user_id):
            if contact.get("status") == "active" and contact.get("display_name", "").strip().casefold() == display_name.casefold():
                raise AppError("Contato ja existe.", code="reimbursement_contact_duplicate")
        record = self.repository.create_reimbursement_contact(
            user_id,
            {**payload.model_dump(mode="json"), "display_name": display_name},
        )
        self._event(user_id, "contact_created", contact_id=record["id"])
        return ReimbursementContactRead(**record)

    def update_contact(self, user_id: str, contact_id: str, payload: ReimbursementContactUpdate) -> ReimbursementContactRead:
        current = self._contact(user_id, contact_id)
        data = payload.model_dump(mode="json", exclude_unset=True)
        if "display_name" in data and data["display_name"]:
            data["display_name"] = data["display_name"].strip()
            for contact in self.repository.list_reimbursement_contacts(user_id):
                if contact["id"] == current["id"] or contact.get("status") != "active":
                    continue
                if contact.get("display_name", "").strip().casefold() == data["display_name"].casefold():
                    raise AppError("Contato ja existe.", code="reimbursement_contact_duplicate")
        record = self.repository.update_reimbursement_contact(user_id, current["id"], data)
        if not record:
            raise AppError("Contato nao encontrado.", status_code=404, code="reimbursement_contact_not_found")
        self._event(user_id, "contact_updated", contact_id=record["id"])
        return ReimbursementContactRead(**record)

    def delete_contact(self, user_id: str, contact_id: str) -> ReimbursementContactRead:
        return self.update_contact(user_id, contact_id, ReimbursementContactUpdate(status="inactive"))

    def list_claims(self, user_id: str) -> list[ReimbursementClaimRead]:
        return [self._claim_read(user_id, item) for item in self.repository.list_reimbursement_claims(user_id)]

    def overview(self, user_id: str) -> ReimbursementOverviewRead:
        claims = self.list_claims(user_id)
        sent_claims = [claim for claim in claims if claim.status == ReimbursementClaimStatus.sent]
        draft_claims = [claim for claim in claims if claim.status == ReimbursementClaimStatus.draft]
        canceled_claims = [claim for claim in claims if claim.status == ReimbursementClaimStatus.canceled]
        upcoming_claims = sorted(
            [claim for claim in sent_claims if claim.due_date],
            key=lambda claim: claim.due_date or "",
        )[:5]
        return ReimbursementOverviewRead(
            total_sent=sum((claim.total_amount for claim in sent_claims), Decimal("0.00")).quantize(Decimal("0.01")),
            draft_count=len(draft_claims),
            sent_count=len(sent_claims),
            canceled_count=len(canceled_claims),
            recent_claims=claims[:5],
            draft_claims=draft_claims[:5],
            upcoming_claims=upcoming_claims,
        )

    def get_claim(self, user_id: str, claim_id: str) -> ReimbursementClaimRead:
        return self._claim_read(user_id, self._claim(user_id, claim_id))

    def create_claim(self, user_id: str, payload: ReimbursementClaimCreate) -> ReimbursementClaimRead:
        contact = self._contact(user_id, payload.contact_id)
        if contact.get("status") != "active":
            raise AppError("Contato inativo nao pode receber cobranca.", code="reimbursement_contact_inactive")
        record = self.repository.create_reimbursement_claim(user_id, payload.model_dump(mode="json"))
        self._event(user_id, "claim_created", claim_id=record["id"], contact_id=contact["id"])
        return self._claim_read(user_id, record)

    def update_claim(self, user_id: str, claim_id: str, payload: ReimbursementClaimUpdate) -> ReimbursementClaimRead:
        claim = self._claim(user_id, claim_id)
        self._ensure_draft(claim)
        data = payload.model_dump(mode="json", exclude_unset=True)
        if data.get("contact_id"):
            contact = self._contact(user_id, data["contact_id"])
            if contact.get("status") != "active":
                raise AppError("Contato inativo nao pode receber cobranca.", code="reimbursement_contact_inactive")
        record = self.repository.update_reimbursement_claim(user_id, claim_id, data)
        if not record:
            raise AppError("Cobranca nao encontrada.", status_code=404, code="reimbursement_claim_not_found")
        self._event(user_id, "claim_updated", claim_id=claim_id, contact_id=record.get("contact_id"))
        return self._claim_read(user_id, record)

    def add_item(self, user_id: str, claim_id: str, payload: ReimbursementItemCreate) -> ReimbursementClaimRead:
        claim = self._claim(user_id, claim_id)
        self._ensure_draft(claim)
        transaction = self._reimbursable_transaction(user_id, payload.transaction_id)
        amount = Decimal(str(payload.amount_requested))
        if any(item.get("transaction_id") == transaction["id"] and item.get("status") == ReimbursementItemStatus.active.value for item in self._active_items(user_id, claim_id)):
            raise AppError("Transacao ja adicionada nesta cobranca.", code="reimbursement_item_duplicate")
        position = len(self.repository.list_reimbursement_items(user_id, claim_id))
        payload_data = {
            "claim_id": claim_id,
            "transaction_id": transaction["id"],
            "amount_requested": amount,
            "transaction_snapshot": self._snapshot(transaction, amount),
            "position": position,
        }
        create_atomically = getattr(self.repository, "create_reimbursement_item_with_allocation", None)
        if create_atomically:
            result = create_atomically(user_id, payload_data)
            self._raise_allocation_error(result.get("error"))
            item = result["item"]
        else:
            self._ensure_available_amount(user_id, transaction, amount)
            item = self.repository.create_reimbursement_item(user_id, payload_data)
        self._event(user_id, "item_added", claim_id=claim_id, item_id=item["id"], metadata={"transaction_id": transaction["id"]})
        return self.get_claim(user_id, claim_id)

    def update_item(self, user_id: str, claim_id: str, item_id: str, payload: ReimbursementItemUpdate) -> ReimbursementClaimRead:
        claim = self._claim(user_id, claim_id)
        self._ensure_draft(claim)
        item = self._item(user_id, item_id)
        if item["claim_id"] != claim_id or item.get("status") != ReimbursementItemStatus.active.value:
            raise AppError("Item nao encontrado.", status_code=404, code="reimbursement_item_not_found")
        transaction = self._reimbursable_transaction(user_id, item["transaction_id"])
        amount = Decimal(str(payload.amount_requested))
        data = {"amount_requested": amount, "transaction_snapshot": self._snapshot(transaction, amount)}
        update_atomically = getattr(self.repository, "update_reimbursement_item_with_allocation", None)
        if update_atomically:
            result = update_atomically(user_id, item_id, data)
            self._raise_allocation_error(result.get("error"))
            updated = result["item"]
        else:
            self._ensure_available_amount(user_id, transaction, amount, excluding_item_id=item_id)
            updated = self.repository.update_reimbursement_item(user_id, item_id, data)
        if not updated:
            raise AppError("Item nao encontrado.", status_code=404, code="reimbursement_item_not_found")
        self._event(user_id, "item_updated", claim_id=claim_id, item_id=item_id)
        return self.get_claim(user_id, claim_id)

    def remove_item(self, user_id: str, claim_id: str, item_id: str) -> ReimbursementClaimRead:
        claim = self._claim(user_id, claim_id)
        self._ensure_draft(claim)
        item = self._item(user_id, item_id)
        if item["claim_id"] != claim_id:
            raise AppError("Item nao encontrado.", status_code=404, code="reimbursement_item_not_found")
        self.repository.update_reimbursement_item(
            user_id,
            item_id,
            {"status": ReimbursementItemStatus.canceled.value, "canceled_at": _utcnow()},
        )
        self._event(user_id, "item_removed", claim_id=claim_id, item_id=item_id)
        return self.get_claim(user_id, claim_id)

    def send_claim(self, user_id: str, claim_id: str) -> ReimbursementClaimRead:
        claim = self._claim(user_id, claim_id)
        self._ensure_draft(claim)
        self._refresh_claim_snapshots(user_id, claim_id)
        items = self._active_items(user_id, claim_id)
        if not items:
            raise AppError("Cobranca precisa ter ao menos um item.", code="reimbursement_claim_without_items")
        total = self._items_total(items)
        if total <= Decimal("0"):
            raise AppError("Total da cobranca precisa ser maior que zero.", code="reimbursement_claim_total_invalid")
        record = self.repository.update_reimbursement_claim(
            user_id,
            claim_id,
            {"status": ReimbursementClaimStatus.sent.value, "sent_at": _utcnow(), "total_snapshot": total},
        )
        self._event(user_id, "claim_sent", claim_id=claim_id, metadata={"total_snapshot": str(total)})
        return self._claim_read(user_id, record or self._claim(user_id, claim_id))

    def cancel_claim(self, user_id: str, claim_id: str) -> ReimbursementClaimRead:
        claim = self._claim(user_id, claim_id)
        if claim["status"] in {ReimbursementClaimStatus.paid.value, ReimbursementClaimStatus.canceled.value}:
            raise AppError("Cobranca nao pode ser cancelada neste status.", code="reimbursement_claim_cancel_forbidden")
        total = self._items_total(self._active_items(user_id, claim_id))
        record = self.repository.update_reimbursement_claim(
            user_id,
            claim_id,
            {"status": ReimbursementClaimStatus.canceled.value, "canceled_at": _utcnow(), "total_snapshot": claim.get("total_snapshot") or total},
        )
        for item in self._active_items(user_id, claim_id):
            self.repository.update_reimbursement_item(
                user_id,
                item["id"],
                {"status": ReimbursementItemStatus.canceled.value, "canceled_at": _utcnow()},
            )
        self._event(user_id, "claim_canceled", claim_id=claim_id)
        return self._claim_read(user_id, record or self._claim(user_id, claim_id))

    def refresh_claim_snapshots(self, user_id: str, claim_id: str) -> ReimbursementClaimRead:
        claim = self._claim(user_id, claim_id)
        self._ensure_draft(claim)
        self._refresh_claim_snapshots(user_id, claim_id)
        self._event(user_id, "claim_snapshots_refreshed", claim_id=claim_id)
        return self.get_claim(user_id, claim_id)

    def list_events(self, user_id: str, claim_id: str) -> list[ReimbursementEventRead]:
        self._claim(user_id, claim_id)
        list_events = getattr(self.repository, "list_reimbursement_events", None)
        if not list_events:
            return []
        return [ReimbursementEventRead(**item) for item in list_events(user_id, claim_id)]

    def list_comments(self, viewer_user_id: str, claim_id: str, limit: int = 50, cursor: str | None = None) -> list[ReimbursementCommentRead]:
        access = self._comment_access(viewer_user_id, claim_id)
        list_comments = getattr(self.repository, "list_reimbursement_comments", None)
        if not list_comments:
            return []
        limit = max(1, min(limit, 100))
        comments = list_comments(access["owner_user_id"], claim_id, limit=limit, cursor=cursor)
        return [self._comment_read(viewer_user_id, access, item) for item in comments]

    def create_comment(self, user: Any, claim_id: str, payload: ReimbursementCommentCreate) -> ReimbursementCommentRead:
        access = self._comment_access(user.id, claim_id)
        create_comment = getattr(self.repository, "create_reimbursement_comment", None)
        if not create_comment:
            raise AppError("Repositorio nao suporta comentarios.", code="reimbursement_comments_unavailable")
        body = payload.body.strip()
        if not body:
            raise AppError("Comentario nao pode ficar vazio.", code="reimbursement_comment_empty")
        comment = create_comment(
            access["owner_user_id"],
            {
                "claim_id": claim_id,
                "author_user_id": user.id,
                "author_role": access["role"],
                "body": body,
                "created_at": _utcnow(),
            },
        )
        self._event(
            access["owner_user_id"],
            "comment_created",
            claim_id=claim_id,
            contact_id=access["claim"].get("contact_id"),
            metadata={"comment_id": comment["id"], "author_role": access["role"]},
            actor_type=access["role"],
            actor_user_id=user.id,
        )
        return self._comment_read(user.id, access, comment)

    def delete_comment(self, user: Any, claim_id: str, comment_id: str) -> dict[str, str]:
        access = self._comment_access(user.id, claim_id)
        get_comment = getattr(self.repository, "get_reimbursement_comment", None)
        update_comment = getattr(self.repository, "update_reimbursement_comment", None)
        if not get_comment or not update_comment:
            raise AppError("Repositorio nao suporta comentarios.", code="reimbursement_comments_unavailable")
        comment = get_comment(access["owner_user_id"], comment_id)
        if not comment or comment.get("claim_id") != claim_id:
            raise AppError("Comentario nao encontrado.", status_code=404, code="reimbursement_comment_not_found")
        if comment.get("deleted_at"):
            raise AppError("Comentario ja foi excluido.", status_code=409, code="reimbursement_comment_already_deleted")
        can_delete = comment.get("author_user_id") == user.id or access["role"] == ReimbursementCommentAuthorRole.owner.value
        if not can_delete:
            raise AppError("Voce nao tem permissao para excluir este comentario.", status_code=403, code="reimbursement_comment_delete_forbidden")
        updated = update_comment(
            access["owner_user_id"],
            comment_id,
            {
                "deleted_at": _utcnow(),
                "deleted_by_user_id": user.id,
                "deleted_by_role": access["role"],
            },
        )
        self._event(
            access["owner_user_id"],
            "comment_deleted",
            claim_id=claim_id,
            contact_id=access["claim"].get("contact_id"),
            metadata={"comment_id": comment_id, "author_role": comment.get("author_role"), "deleted_by_role": access["role"]},
            actor_type=access["role"],
            actor_user_id=user.id,
        )
        if not updated:
            raise AppError("Comentario nao encontrado.", status_code=404, code="reimbursement_comment_not_found")
        return {"status": "deleted"}

    def list_invitations(self, user_id: str) -> list[ReimbursementInvitationRead]:
        list_invitations = getattr(self.repository, "list_reimbursement_invitations", None)
        if not list_invitations:
            return []
        return [self._invitation_read(user_id, item) for item in list_invitations(user_id)]

    def create_invitation(self, user_id: str, payload: ReimbursementInvitationCreate) -> ReimbursementInvitationCreatedRead:
        create_invitation = getattr(self.repository, "create_reimbursement_invitation", None)
        if not create_invitation:
            raise AppError("Repositorio nao suporta convites.", code="reimbursement_invitations_unavailable")
        contact = self._contact(user_id, payload.contact_id)
        if contact.get("status") != "active":
            raise AppError("Contato inativo nao pode receber convite.", code="reimbursement_contact_inactive")
        claim_id = payload.claim_id
        if claim_id:
            claim = self._claim(user_id, claim_id)
            if claim.get("contact_id") != contact["id"]:
                raise AppError("Cobranca nao pertence a este contato.", code="reimbursement_claim_contact_mismatch")
            if claim.get("status") == ReimbursementClaimStatus.draft.value:
                raise AppError("Finalize a cobranca antes de compartilhar acesso.", code="reimbursement_claim_not_sent")
        email = (payload.email or contact.get("email") or "").strip().casefold()
        if not email:
            raise AppError("Informe um e-mail para o convite.", code="reimbursement_invitation_email_required")
        token = secrets.token_urlsafe(32)
        record = create_invitation(
            user_id,
            {
                "contact_id": contact["id"],
                "claim_id": claim_id,
                "email": email,
                "token_hash": self._token_hash(token),
                "status": ReimbursementInvitationStatus.pending.value,
                "expires_at": _utcnow() + timedelta(days=payload.expires_in_days),
                "created_at": _utcnow(),
            },
        )
        self._event(user_id, "invitation_created", contact_id=contact["id"], claim_id=claim_id)
        return ReimbursementInvitationCreatedRead(
            **self._invitation_read(user_id, record).model_dump(),
            accept_token=token,
            accept_path=f"/guest/reimbursements/accept?token={token}",
        )

    def revoke_invitation(self, user_id: str, invitation_id: str) -> ReimbursementInvitationRead:
        invitation = self._invitation(user_id, invitation_id)
        if invitation.get("status") != ReimbursementInvitationStatus.pending.value:
            raise AppError("Convite nao pode ser revogado neste status.", code="reimbursement_invitation_revoke_forbidden")
        record = self.repository.update_reimbursement_invitation(
            user_id,
            invitation_id,
            {"status": ReimbursementInvitationStatus.revoked.value, "revoked_at": _utcnow()},
        )
        self._event(user_id, "invitation_revoked", contact_id=invitation["contact_id"], claim_id=invitation.get("claim_id"))
        return self._invitation_read(user_id, record or invitation)

    def list_memberships(self, user_id: str) -> list[ReimbursementMembershipRead]:
        list_memberships = getattr(self.repository, "list_reimbursement_memberships", None)
        if not list_memberships:
            return []
        return [self._membership_read(user_id, item) for item in list_memberships(user_id)]

    def revoke_membership(self, user_id: str, membership_id: str) -> ReimbursementMembershipRead:
        membership = self._membership(user_id, membership_id)
        if membership.get("status") != ReimbursementMembershipStatus.active.value:
            raise AppError("Acesso ja esta revogado.", code="reimbursement_membership_revoke_forbidden")
        record = self.repository.update_reimbursement_membership(
            user_id,
            membership_id,
            {"status": ReimbursementMembershipStatus.revoked.value, "revoked_at": _utcnow()},
        )
        self._event(user_id, "membership_revoked", contact_id=membership["contact_id"])
        return self._membership_read(user_id, record or membership)

    def accept_invitation(self, user: Any, payload: ReimbursementInvitationAccept, client_ip: str | None = None) -> ReimbursementMembershipRead:
        user_email = (getattr(user, "email", None) or "").strip().casefold()
        if not user_email:
            raise AppError("Entre com o e-mail convidado para aceitar.", code="reimbursement_guest_email_required")
        ensure_profile = getattr(self.repository, "ensure_profile", None)
        if ensure_profile:
            ensure_profile(user.id, email=user_email, full_name=getattr(user, "full_name", None))
        token_hash = self._token_hash(payload.token)
        attempt_id = self._begin_invitation_accept_attempt(token_hash=token_hash, user_id=user.id, client_ip=client_ip)
        failure_code = "reimbursement_invitation_invalid"
        success = False
        try:
            membership = self._accept_invitation_after_rate_limit(user, user_email, token_hash)
            success = True
            failure_code = None
            return membership
        except AppError as exc:
            failure_code = exc.code
            raise
        finally:
            self._complete_invitation_accept_attempt(attempt_id, success=success, failure_code=failure_code)

    def _accept_invitation_after_rate_limit(self, user: Any, user_email: str, token_hash: str) -> ReimbursementMembershipRead:
        accept_atomically = getattr(self.repository, "accept_reimbursement_invitation_atomic", None)
        if accept_atomically:
            result = accept_atomically(token_hash, user.id, user_email, _utcnow())
            if result.get("error"):
                raise AppError("Convite invalido ou expirado.", status_code=404, code="reimbursement_invitation_invalid")
            membership = result["membership"]
            invitation = result.get("invitation") or {}
            self._event(
                membership["owner_user_id"],
                "invitation_accepted",
                contact_id=membership["contact_id"],
                claim_id=invitation.get("claim_id"),
                actor_type="guest",
                actor_user_id=user.id,
            )
            return self._membership_read(membership["owner_user_id"], membership)
        get_by_token = getattr(self.repository, "get_reimbursement_invitation_by_token_hash", None)
        if not get_by_token:
            raise AppError("Repositorio nao suporta convites.", code="reimbursement_invitations_unavailable")
        invitation = get_by_token(token_hash)
        if not invitation:
            raise AppError("Convite invalido ou expirado.", status_code=404, code="reimbursement_invitation_invalid")
        if invitation.get("status") != ReimbursementInvitationStatus.pending.value or self._as_datetime(invitation["expires_at"]) < _utcnow():
            raise AppError("Convite invalido ou expirado.", status_code=404, code="reimbursement_invitation_invalid")
        if user_email != str(invitation["email"]).strip().casefold():
            raise AppError("Este convite pertence a outro e-mail.", status_code=404, code="reimbursement_invitation_invalid")
        owner_id = invitation["owner_user_id"]
        contact = self._contact(owner_id, invitation["contact_id"])
        if contact.get("status") != "active":
            raise AppError("Convite invalido ou expirado.", status_code=404, code="reimbursement_invitation_invalid")
        existing = self.repository.get_active_reimbursement_membership(owner_id, contact["id"], user.id)
        if existing:
            membership = existing
        else:
            membership = self.repository.create_reimbursement_membership(
                owner_id,
                {
                    "contact_id": contact["id"],
                    "auth_user_id": user.id,
                    "email": user_email,
                    "status": ReimbursementMembershipStatus.active.value,
                    "linked_at": _utcnow(),
                    "created_at": _utcnow(),
                },
            )
        self.repository.update_reimbursement_invitation(
            owner_id,
            invitation["id"],
            {
                "status": ReimbursementInvitationStatus.accepted.value,
                "accepted_at": _utcnow(),
                "accepted_by_user_id": user.id,
            },
        )
        self._event(owner_id, "invitation_accepted", contact_id=contact["id"], claim_id=invitation.get("claim_id"), actor_type="guest", actor_user_id=user.id)
        return self._membership_read(owner_id, membership)

    def list_guest_claims(self, guest_user_id: str) -> list[GuestReimbursementClaimRead]:
        list_claims = getattr(self.repository, "list_guest_reimbursement_claims", None)
        if not list_claims:
            return []
        return [self._guest_claim_read(item["owner_user_id"], item) for item in list_claims(guest_user_id)]

    def get_guest_claim(self, guest_user_id: str, claim_id: str) -> GuestReimbursementClaimRead:
        claim = self._guest_claim(guest_user_id, claim_id)
        self.repository.update_reimbursement_claim(
            claim["owner_user_id"],
            claim["id"],
            {
                "first_viewed_at": claim.get("first_viewed_at") or _utcnow(),
                "last_viewed_at": _utcnow(),
                "view_count": int(claim.get("view_count") or 0) + 1,
            },
        )
        self._event(claim["owner_user_id"], "claim_viewed", claim_id=claim["id"], contact_id=claim["contact_id"], actor_type="guest", actor_user_id=guest_user_id)
        return self._guest_claim_read(claim["owner_user_id"], self._claim(claim["owner_user_id"], claim["id"]))

    def acknowledge_guest_claim(self, guest_user_id: str, claim_id: str) -> GuestReimbursementClaimRead:
        claim = self._guest_claim(guest_user_id, claim_id)
        if claim["status"] == ReimbursementClaimStatus.acknowledged.value:
            return self._guest_claim_read(claim["owner_user_id"], claim)
        if claim["status"] not in {ReimbursementClaimStatus.sent.value, ReimbursementClaimStatus.disputed.value}:
            raise AppError("Cobranca nao pode ser reconhecida neste status.", code="reimbursement_claim_transition_forbidden")
        record = self.repository.update_reimbursement_claim(
            claim["owner_user_id"],
            claim["id"],
            {"status": ReimbursementClaimStatus.acknowledged.value},
        )
        self._event(claim["owner_user_id"], "claim_acknowledged", claim_id=claim["id"], contact_id=claim["contact_id"], actor_type="guest", actor_user_id=guest_user_id)
        return self._guest_claim_read(claim["owner_user_id"], record or claim)

    def dispute_guest_claim(self, guest_user_id: str, claim_id: str, payload: GuestReimbursementAction) -> GuestReimbursementClaimRead:
        claim = self._guest_claim(guest_user_id, claim_id)
        if claim["status"] not in {ReimbursementClaimStatus.sent.value, ReimbursementClaimStatus.acknowledged.value}:
            raise AppError("Cobranca nao pode ser contestada neste status.", code="reimbursement_claim_transition_forbidden")
        note = (payload.note or "").strip()
        if not note:
            raise AppError("Informe o motivo da contestacao.", code="reimbursement_dispute_note_required")
        record = self.repository.update_reimbursement_claim(
            claim["owner_user_id"],
            claim["id"],
            {"status": ReimbursementClaimStatus.disputed.value},
        )
        self._event(
            claim["owner_user_id"],
            "claim_disputed",
            claim_id=claim["id"],
            contact_id=claim["contact_id"],
            actor_type="guest",
            actor_user_id=guest_user_id,
            metadata={"note": note[:500]} if note else {},
        )
        return self._guest_claim_read(claim["owner_user_id"], record or claim)

    def add_claim_attachment(self, user_id: str, claim_id: str, payload: ReimbursementClaimAttachmentCreate) -> ReimbursementClaimAttachmentRead:
        claim = self._claim(user_id, claim_id)
        stored_file = self.repository.get_stored_file(user_id, payload.file_id)
        if not stored_file:
            raise AppError("Arquivo nao encontrado.", status_code=404, code="file_not_found")
        create_attachment = getattr(self.repository, "create_reimbursement_claim_attachment", None)
        if not create_attachment:
            raise AppError("Repositorio nao suporta comprovantes de cobranca.", code="reimbursement_claim_attachments_unavailable")
        attachment = create_attachment(user_id, {"claim_id": claim["id"], "file_id": payload.file_id})
        self._event(user_id, "claim_attachment_shared", claim_id=claim["id"], contact_id=claim["contact_id"], metadata={"file_id": payload.file_id})
        return self._claim_attachment_read(user_id, attachment)

    def list_claim_attachments(self, user_id: str, claim_id: str) -> list[ReimbursementClaimAttachmentRead]:
        self._claim(user_id, claim_id)
        list_attachments = getattr(self.repository, "list_reimbursement_claim_attachments", None)
        if not list_attachments:
            return []
        return [self._claim_attachment_read(user_id, item) for item in list_attachments(user_id, claim_id)]

    def remove_claim_attachment(self, user_id: str, claim_id: str, attachment_id: str) -> dict[str, str]:
        claim = self._claim(user_id, claim_id)
        attachment = self.repository.get_reimbursement_claim_attachment(user_id, attachment_id)
        if not attachment or attachment.get("claim_id") != claim_id:
            raise AppError("Comprovante nao encontrado.", status_code=404, code="reimbursement_claim_attachment_not_found")
        self.repository.update_reimbursement_claim_attachment(user_id, attachment_id, {"status": "inactive", "deleted_at": _utcnow()})
        self._event(user_id, "claim_attachment_removed", claim_id=claim["id"], contact_id=claim["contact_id"], metadata={"file_id": attachment["file_id"]})
        return {"status": "deleted"}

    def list_guest_claim_attachments(self, guest_user_id: str, claim_id: str) -> list[ReimbursementClaimAttachmentRead]:
        claim = self._guest_claim(guest_user_id, claim_id)
        return self.list_claim_attachments(claim["owner_user_id"], claim["id"])

    def guest_claim_attachment_file(self, guest_user_id: str, claim_id: str, attachment_id: str) -> tuple[str, str]:
        claim = self._guest_claim(guest_user_id, claim_id)
        attachment = self.repository.get_reimbursement_claim_attachment(claim["owner_user_id"], attachment_id)
        if not attachment or attachment.get("claim_id") != claim["id"] or attachment.get("status") != "active":
            raise AppError("Comprovante nao encontrado.", status_code=404, code="reimbursement_claim_attachment_not_found")
        return claim["owner_user_id"], attachment["file_id"]

    def list_eligible_transactions(self, user_id: str, query: str | None = None, limit: int = 30) -> list[ReimbursementEligibleTransactionRead]:
        limit = max(1, min(limit, 100))
        list_candidates = getattr(self.repository, "list_reimbursement_candidate_transactions", None)
        if list_candidates:
            records = list_candidates(user_id, query=query, limit=limit)
        else:
            records = self.repository.list_transactions(user_id)[:limit]
        results = []
        for record in records:
            allocated = Decimal(str(record.get("allocated_amount", "0") or "0")).quantize(Decimal("0.01"))
            amount = abs(Decimal(str(record["amount"]))).quantize(Decimal("0.01"))
            available = max(amount - allocated, Decimal("0.00")).quantize(Decimal("0.01"))
            eligible = record.get("type") == TransactionType.expense.value and record.get("status") != "ignored" and available > 0
            reason = None
            if record.get("type") != TransactionType.expense.value:
                reason = "not_expense"
            elif record.get("status") == "ignored":
                reason = "inactive"
            elif available <= 0:
                reason = "fully_allocated"
            results.append(
                ReimbursementEligibleTransactionRead(
                    id=record["id"],
                    transaction_date=str(record["transaction_date"]),
                    description=record["description"],
                    amount=amount,
                    type=record["type"],
                    status=record["status"],
                    category_id=record.get("category_id"),
                    account_id=record.get("account_id"),
                    card_id=record.get("card_id"),
                    card_statement_id=record.get("card_statement_id"),
                    allocated_amount=allocated,
                    available_amount=available,
                    eligible=eligible,
                    ineligible_reason=reason,
                )
            )
        return results

    def _contact(self, user_id: str, contact_id: str) -> dict[str, Any]:
        contact = self.repository.get_reimbursement_contact(user_id, contact_id)
        if not contact:
            raise AppError("Contato nao encontrado.", status_code=404, code="reimbursement_contact_not_found")
        return contact

    def _claim(self, user_id: str, claim_id: str) -> dict[str, Any]:
        claim = self.repository.get_reimbursement_claim(user_id, claim_id)
        if not claim:
            raise AppError("Cobranca nao encontrada.", status_code=404, code="reimbursement_claim_not_found")
        return claim

    def _item(self, user_id: str, item_id: str) -> dict[str, Any]:
        item = self.repository.get_reimbursement_item(user_id, item_id)
        if not item:
            raise AppError("Item nao encontrado.", status_code=404, code="reimbursement_item_not_found")
        return item

    def _invitation(self, user_id: str, invitation_id: str) -> dict[str, Any]:
        invitation = self.repository.get_reimbursement_invitation(user_id, invitation_id)
        if not invitation:
            raise AppError("Convite nao encontrado.", status_code=404, code="reimbursement_invitation_not_found")
        return invitation

    def _membership(self, user_id: str, membership_id: str) -> dict[str, Any]:
        membership = self.repository.get_reimbursement_membership(user_id, membership_id)
        if not membership:
            raise AppError("Acesso nao encontrado.", status_code=404, code="reimbursement_membership_not_found")
        return membership

    def _guest_claim(self, guest_user_id: str, claim_id: str) -> dict[str, Any]:
        get_guest_claim = getattr(self.repository, "get_guest_reimbursement_claim", None)
        if not get_guest_claim:
            raise AppError("Repositorio nao suporta portal convidado.", code="reimbursement_guest_unavailable")
        claim = get_guest_claim(guest_user_id, claim_id)
        if not claim:
            raise AppError("Cobranca nao encontrada.", status_code=404, code="reimbursement_claim_not_found")
        return claim

    def _comment_access(self, viewer_user_id: str, claim_id: str) -> dict[str, Any]:
        owner_claim = self.repository.get_reimbursement_claim(viewer_user_id, claim_id)
        if owner_claim:
            return {"role": ReimbursementCommentAuthorRole.owner.value, "owner_user_id": viewer_user_id, "claim": owner_claim}
        claim = self._guest_claim(viewer_user_id, claim_id)
        if claim.get("status") not in GUEST_SHARED_CLAIM_STATUSES:
            raise AppError("Cobranca nao encontrada.", status_code=404, code="reimbursement_claim_not_found")
        return {"role": ReimbursementCommentAuthorRole.guest.value, "owner_user_id": claim["owner_user_id"], "claim": claim}

    def _comment_read(self, viewer_user_id: str, access: dict[str, Any], comment: dict[str, Any]) -> ReimbursementCommentRead:
        is_mine = comment["author_user_id"] == viewer_user_id
        if is_mine:
            label = "Voce"
        elif access["role"] == ReimbursementCommentAuthorRole.owner.value and comment.get("author_role") == ReimbursementCommentAuthorRole.guest.value:
            label = "Responsavel"
        elif comment.get("author_role") == ReimbursementCommentAuthorRole.owner.value:
            label = "Titular"
        else:
            label = "Responsavel"
        return ReimbursementCommentRead(
            id=comment["id"],
            claim_id=comment["claim_id"],
            author_role=comment["author_role"],
            author_label=label,
            is_mine=is_mine,
            body=comment["body"],
            created_at=comment["created_at"],
            updated_at=comment.get("updated_at"),
        )

    def _token_hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _ip_hash(self, client_ip: str | None) -> str:
        source = (client_ip or "unknown").strip() or "unknown"
        secret = settings.jwt_secret or "change-me-local-only"
        return hmac.new(secret.encode("utf-8"), source.encode("utf-8"), hashlib.sha256).hexdigest()

    def _begin_invitation_accept_attempt(self, token_hash: str, user_id: str, client_ip: str | None) -> str | None:
        if not settings.invitation_accept_rate_limit_enabled:
            return None
        begin_attempt = getattr(self.repository, "begin_invitation_accept_attempt", None)
        if not begin_attempt:
            return None
        now = _utcnow()
        window_started_at = now - timedelta(seconds=settings.invitation_accept_rate_limit_window_seconds)
        result = begin_attempt(
            token_hash=token_hash,
            ip_hash=self._ip_hash(client_ip),
            auth_user_id=user_id,
            max_attempts=settings.invitation_accept_rate_limit_max_attempts,
            window_started_at=window_started_at,
            attempted_at=now,
        )
        if not result.get("allowed"):
            raise AppError("Muitas tentativas. Tente novamente mais tarde.", status_code=429, code="reimbursement_invitation_rate_limited")
        return result.get("attempt_id")

    def _complete_invitation_accept_attempt(self, attempt_id: str | None, *, success: bool, failure_code: str | None) -> None:
        if not attempt_id:
            return
        complete_attempt = getattr(self.repository, "complete_invitation_accept_attempt", None)
        if complete_attempt:
            complete_attempt(attempt_id, success=success, failure_code=failure_code)

    def _as_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    def _ensure_draft(self, claim: dict[str, Any]) -> None:
        if claim["status"] != ReimbursementClaimStatus.draft.value:
            raise AppError("Apenas cobrancas em rascunho podem ser editadas.", code="reimbursement_claim_not_draft")

    def _reimbursable_transaction(self, user_id: str, transaction_id: str) -> dict[str, Any]:
        transaction = self.repository.get_transaction(user_id, transaction_id)
        if not transaction:
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")
        if transaction.get("type") != TransactionType.expense.value:
            raise AppError("Apenas despesas podem ser ressarcidas no MVP.", code="transaction_not_reimbursable")
        if Decimal(str(transaction.get("amount", "0"))) == Decimal("0"):
            raise AppError("Transacao sem valor ressarcivel.", code="transaction_not_reimbursable")
        return transaction

    def _reimbursable_amount(self, transaction: dict[str, Any]) -> Decimal:
        return abs(Decimal(str(transaction["amount"]))).quantize(Decimal("0.01"))

    def _ensure_available_amount(
        self,
        user_id: str,
        transaction: dict[str, Any],
        requested: Decimal,
        excluding_item_id: str | None = None,
    ) -> None:
        requested = requested.quantize(Decimal("0.01"))
        allocated = Decimal("0.00")
        for item in self.repository.list_reimbursement_items_by_transaction(user_id, transaction["id"]):
            if excluding_item_id and item["id"] == excluding_item_id:
                continue
            allocated += Decimal(str(item["amount_requested"]))
        if allocated + requested > self._reimbursable_amount(transaction):
            raise AppError("Valor solicitado excede o saldo ressarcivel da transacao.", code="reimbursement_amount_exceeds_transaction")

    def _raise_allocation_error(self, error: str | None) -> None:
        if not error:
            return
        if error == "transaction_not_found":
            raise AppError("Transacao nao encontrada.", status_code=404, code="transaction_not_found")
        if error == "transaction_not_reimbursable":
            raise AppError("Apenas despesas podem ser ressarcidas no MVP.", code="transaction_not_reimbursable")
        if error == "reimbursement_item_duplicate":
            raise AppError("Transacao ja adicionada nesta cobranca.", code="reimbursement_item_duplicate")
        if error == "reimbursement_item_not_found":
            raise AppError("Item nao encontrado.", status_code=404, code="reimbursement_item_not_found")
        if error == "reimbursement_amount_exceeds_transaction":
            raise AppError("Valor solicitado excede o saldo ressarcivel da transacao.", code="reimbursement_amount_exceeds_transaction")
        raise AppError("Falha ao validar alocacao do ressarcimento.", code=error)

    def _snapshot(self, transaction: dict[str, Any], amount_requested: Decimal) -> dict[str, Any]:
        snapshot = {
            "transaction_id": transaction["id"],
            "description": transaction["description"],
            "original_description": transaction.get("original_description"),
            "normalized_description": transaction.get("normalized_description"),
            "transaction_date": transaction["transaction_date"],
            "amount": str(transaction["amount"]),
            "amount_requested": str(amount_requested.quantize(Decimal("0.01"))),
            "type": transaction["type"],
            "category_id": transaction.get("category_id"),
            "account_id": transaction.get("account_id"),
            "card_id": transaction.get("card_id"),
            "card_statement_id": transaction.get("card_statement_id"),
            "currency": "BRL",
            "snapshot_version": 1,
        }
        snapshot["source_signature"] = self._snapshot_signature(transaction)
        snapshot["finalized_at"] = None
        return snapshot

    def _final_snapshot(self, transaction: dict[str, Any], amount_requested: Decimal) -> dict[str, Any]:
        snapshot = self._snapshot(transaction, amount_requested)
        snapshot["finalized_at"] = _utcnow().isoformat()
        return snapshot

    def _snapshot_signature(self, transaction: dict[str, Any]) -> str:
        fields = [
            transaction.get("transaction_date"),
            transaction.get("description"),
            transaction.get("original_description"),
            transaction.get("normalized_description"),
            str(transaction.get("amount")),
            transaction.get("type"),
            transaction.get("category_id"),
            transaction.get("account_id"),
            transaction.get("card_id"),
            transaction.get("card_statement_id"),
        ]
        return "|".join("" if value is None else str(value) for value in fields)

    def _snapshot_current(self, item: dict[str, Any]) -> bool | None:
        snapshot = item.get("transaction_snapshot") or {}
        transaction = self.repository.get_transaction(item["owner_user_id"], item["transaction_id"])
        if not transaction:
            return False
        return snapshot.get("source_signature") == self._snapshot_signature(transaction)

    def _refresh_claim_snapshots(self, user_id: str, claim_id: str) -> None:
        for item in self._active_items(user_id, claim_id):
            amount = Decimal(str(item["amount_requested"]))
            transaction = self._reimbursable_transaction(user_id, item["transaction_id"])
            self._ensure_available_amount(user_id, transaction, amount, excluding_item_id=item["id"])
            self.repository.update_reimbursement_item(
                user_id,
                item["id"],
                {"transaction_snapshot": self._final_snapshot(transaction, amount)},
            )

    def _active_items(self, user_id: str, claim_id: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self.repository.list_reimbursement_items(user_id, claim_id)
            if item.get("status") == ReimbursementItemStatus.active.value
        ]

    def _items_total(self, items: list[dict[str, Any]]) -> Decimal:
        return sum((Decimal(str(item["amount_requested"])) for item in items), Decimal("0.00")).quantize(Decimal("0.01"))

    def _claim_read(self, user_id: str, claim: dict[str, Any]) -> ReimbursementClaimRead:
        raw_items = self.repository.list_reimbursement_items(user_id, claim["id"])
        if claim.get("status") != ReimbursementClaimStatus.canceled.value:
            raw_items = [item for item in raw_items if item.get("status") == ReimbursementItemStatus.active.value]
        items = [
            ReimbursementItemRead(**item, snapshot_is_current=self._snapshot_current(item))
            for item in raw_items
        ]
        total = claim.get("total_snapshot")
        total_amount = Decimal(str(total)) if total is not None else sum((item.amount_requested for item in items), Decimal("0.00"))
        contact = self.repository.get_reimbursement_contact(user_id, claim["contact_id"])
        return ReimbursementClaimRead(
            **claim,
            total_amount=total_amount.quantize(Decimal("0.01")),
            contact=ReimbursementContactRead(**contact) if contact else None,
            items=items,
        )

    def _invitation_read(self, user_id: str, invitation: dict[str, Any]) -> ReimbursementInvitationRead:
        status = invitation.get("status")
        if status == ReimbursementInvitationStatus.pending.value and self._as_datetime(invitation["expires_at"]) < _utcnow():
            invitation = {**invitation, "status": ReimbursementInvitationStatus.expired.value}
        contact = self.repository.get_reimbursement_contact(user_id, invitation["contact_id"])
        claim = self.repository.get_reimbursement_claim(user_id, invitation["claim_id"]) if invitation.get("claim_id") else None
        return ReimbursementInvitationRead(
            **invitation,
            contact=ReimbursementContactRead(**contact) if contact else None,
            claim=self._claim_read(user_id, claim) if claim else None,
        )

    def _membership_read(self, user_id: str, membership: dict[str, Any]) -> ReimbursementMembershipRead:
        contact = self.repository.get_reimbursement_contact(user_id, membership["contact_id"])
        return ReimbursementMembershipRead(
            **membership,
            contact=ReimbursementContactRead(**contact) if contact else None,
        )

    def _guest_claim_read(self, user_id: str, claim: dict[str, Any]) -> GuestReimbursementClaimRead:
        raw_items = [
            item
            for item in self.repository.list_reimbursement_items(user_id, claim["id"])
            if item.get("status") == ReimbursementItemStatus.active.value
        ]
        items = []
        for item in raw_items:
            snapshot = item.get("transaction_snapshot") or {}
            items.append(
                GuestReimbursementItemRead(
                    id=item["id"],
                    description=str(snapshot.get("description") or "Transacao"),
                    transaction_date=str(snapshot.get("transaction_date") or ""),
                    amount=Decimal(str(snapshot.get("amount") or "0")).copy_abs().quantize(Decimal("0.01")),
                    amount_requested=Decimal(str(item["amount_requested"])).quantize(Decimal("0.01")),
                    currency=str(snapshot.get("currency") or "BRL"),
                )
            )
        total = claim.get("total_snapshot")
        total_amount = Decimal(str(total)) if total is not None else sum((item.amount_requested for item in items), Decimal("0.00"))
        attachments = getattr(self.repository, "list_reimbursement_claim_attachments", None)
        attachment_count = len(attachments(user_id, claim["id"])) if attachments else 0
        return GuestReimbursementClaimRead(
            id=claim["id"],
            title=claim["title"],
            description=claim.get("description"),
            due_date=str(claim["due_date"]) if claim.get("due_date") else None,
            status=claim["status"],
            total_amount=total_amount.quantize(Decimal("0.01")),
            sent_at=claim.get("sent_at"),
            first_viewed_at=claim.get("first_viewed_at"),
            last_viewed_at=claim.get("last_viewed_at"),
            attachment_count=attachment_count,
            items=items,
        )

    def _claim_attachment_read(self, user_id: str, attachment: dict[str, Any]) -> ReimbursementClaimAttachmentRead:
        stored_file = self.repository.get_stored_file(user_id, attachment["file_id"])
        if not stored_file:
            raise AppError("Arquivo nao encontrado.", status_code=404, code="file_not_found")
        return ReimbursementClaimAttachmentRead(
            id=attachment["id"],
            claim_id=attachment["claim_id"],
            status=attachment.get("status", "active"),
            created_at=attachment["created_at"],
            deleted_at=attachment.get("deleted_at"),
            file=ReimbursementClaimAttachmentFileRead(
                original_filename=stored_file["original_filename"],
                detected_mime_type=stored_file["detected_mime_type"],
                size_bytes=stored_file["size_bytes"],
            ),
        )

    def _event(
        self,
        user_id: str,
        event_type: str,
        *,
        claim_id: str | None = None,
        contact_id: str | None = None,
        item_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        actor_type: str = "owner",
        actor_user_id: str | None = None,
    ) -> None:
        create_event = getattr(self.repository, "create_reimbursement_event", None)
        if not create_event:
            return
        create_event(
            user_id,
            {
                "claim_id": claim_id,
                "contact_id": contact_id,
                "item_id": item_id,
                "event_type": event_type,
                "metadata": metadata or {},
                "actor_type": actor_type,
                "actor_user_id": actor_user_id or (user_id if actor_type == "owner" else None),
            },
        )
