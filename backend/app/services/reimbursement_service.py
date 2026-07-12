from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.core.errors import AppError
from app.models.enums import ReimbursementClaimStatus, ReimbursementItemStatus, TransactionType
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
    ReimbursementItemRead,
    ReimbursementItemUpdate,
    ReimbursementOverviewRead,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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

    def _event(
        self,
        user_id: str,
        event_type: str,
        *,
        claim_id: str | None = None,
        contact_id: str | None = None,
        item_id: str | None = None,
        metadata: dict[str, Any] | None = None,
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
            },
        )
