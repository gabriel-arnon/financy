from __future__ import annotations

from typing import Any

from app.schemas.classification_rules import ClassificationRulePreviewResponse, ClassificationRulePreviewSample
from app.services.structured_rules import evaluate_structured_rule


class ClassificationRulePreviewService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def preview(self, user_id: str, rule: dict[str, Any], sample_limit: int = 5) -> ClassificationRulePreviewResponse:
        category_names = {
            category["id"]: category.get("name")
            for category in self.repository.categories(user_id)
        }
        samples: list[ClassificationRulePreviewSample] = []
        matched_count = 0
        changed_count = 0
        unchanged_count = 0

        for transaction in self.repository.list_transactions(user_id):
            proposed_category_id = self._proposed_category_id(rule, transaction)
            if not proposed_category_id:
                continue

            current_category_id = transaction.get("category_id")
            already_same_category = current_category_id == proposed_category_id
            matched_count += 1
            if already_same_category:
                unchanged_count += 1
            else:
                changed_count += 1

            if len(samples) < sample_limit:
                samples.append(
                    ClassificationRulePreviewSample(
                        transaction_id=transaction["id"],
                        transaction_date=transaction["transaction_date"],
                        description=transaction["description"],
                        amount=transaction["amount"],
                        type=transaction["type"],
                        current_category_id=current_category_id,
                        current_category_name=category_names.get(current_category_id),
                        proposed_category_id=proposed_category_id,
                        proposed_category_name=category_names.get(proposed_category_id),
                        already_same_category=already_same_category,
                    )
                )

        return ClassificationRulePreviewResponse(
            matched_count=matched_count,
            changed_count=changed_count,
            unchanged_count=unchanged_count,
            sample_limit=sample_limit,
            samples=samples,
        )

    def _proposed_category_id(self, rule: dict[str, Any], transaction: dict[str, Any]) -> str | None:
        rule_type = rule.get("transaction_type")
        if rule_type and rule_type != transaction.get("type"):
            return None

        if rule.get("conditions") and rule.get("actions"):
            return self._proposed_category_from_structured_rule(rule, transaction)
        if self._legacy_rule_matches(rule, transaction):
            return rule.get("category_id")
        return None

    def _proposed_category_from_structured_rule(self, rule: dict[str, Any], transaction: dict[str, Any]) -> str | None:
        result = evaluate_structured_rule(
            rule,
            {
                "description": transaction.get("description"),
                "original_description": transaction.get("original_description"),
                "normalized_description": transaction.get("normalized_description"),
                "amount": transaction.get("amount"),
                "category_id": transaction.get("category_id"),
                "external_source": transaction.get("external_source") or transaction.get("source"),
                "payee": transaction.get("payee") or transaction.get("payee_name"),
                "type": transaction.get("type"),
            },
        )
        if not result.matched:
            return None

        for action in result.actions:
            if action.get("type") == "set_category":
                return action.get("category_id")
        return rule.get("category_id")

    def _legacy_rule_matches(self, rule: dict[str, Any], transaction: dict[str, Any]) -> bool:
        keyword = str(rule.get("keyword") or "").strip().upper()
        if not keyword:
            return False

        scope = rule.get("match_scope") or "both"
        haystacks: list[str] = []
        if scope in {"description", "both"}:
            haystacks.append(str(transaction.get("description") or "").upper())
        if scope in {"original_description", "both"}:
            haystacks.append(str(transaction.get("original_description") or "").upper())
        return any(keyword in haystack for haystack in haystacks)
