from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.repositories.local_json import DEFAULT_CLASSIFICATION_SEEDS
from app.services.structured_rules import evaluate_structured_rule


class PostgresCategoriesRulesMixin:
    def categories(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id is None:
            return self._fetch_all("select * from categories where status = 'active' order by is_system desc, name")
        return self._fetch_all(
            """
            select * from categories
            where status = 'active' and (user_id is null or user_id = %s)
            order by is_system desc, name
            """,
            (user_id,),
        )

    def _all_categories(self, user_id: str | None = None) -> list[dict[str, Any]]:
        if user_id is None:
            return self._fetch_all("select * from categories order by is_system desc, name")
        return self._fetch_all(
            "select * from categories where user_id is null or user_id = %s order by is_system desc, name",
            (user_id,),
        )

    def get_category(self, user_id: str, category_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from categories where id = %s and (user_id is null or user_id = %s)",
            (category_id, user_id),
        )

    def find_category_by_name(self, user_id: str, name: str) -> dict[str, Any] | None:
        return self._fetch_one(
            """
            select * from categories
            where lower(trim(name)) = lower(trim(%s)) and (user_id is null or user_id = %s)
            order by is_system desc, status = 'active' desc, created_at desc
            limit 1
            """,
            (name, user_id),
        )

    def create_category(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "categories",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "is_system": False,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_category(self, user_id: str, category_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "categories",
            payload,
            "id = %s and (user_id is null or user_id = %s)",
            (category_id, user_id),
        )

    def delete_category(self, user_id: str, category_id: str) -> dict[str, Any] | None:
        return self.update_category(user_id, category_id, {"status": "inactive"})

    def _ensure_classification_seeds(self, user_id: str) -> None:
        categories_by_name = {category["name"]: category["id"] for category in self.categories()}
        existing = {
            item["keyword"]
            for item in self._fetch_all("select keyword from classification_rules where user_id = %s", (user_id,))
        }
        for keyword, category_name in DEFAULT_CLASSIFICATION_SEEDS:
            category_id = categories_by_name.get(category_name)
            if not category_id or keyword in existing:
                continue
            self.create_classification_rule(
                user_id,
                {
                    "keyword": keyword,
                    "category_id": category_id,
                    "transaction_type": "expense",
                    "priority": 100,
                    "status": "active",
                    "match_scope": "both",
                    "auto_created": False,
                },
            )

    def list_classification_rules(self, user_id: str) -> list[dict[str, Any]]:
        self._ensure_classification_seeds(user_id)
        return self._fetch_all(
            "select * from classification_rules where user_id = %s and status = 'active' order by priority desc, created_at desc",
            (user_id,),
        )

    def _all_classification_rules(self, user_id: str) -> list[dict[str, Any]]:
        self._ensure_classification_seeds(user_id)
        return self._fetch_all(
            "select * from classification_rules where user_id = %s order by priority desc, created_at desc",
            (user_id,),
        )

    def get_classification_rule(self, user_id: str, rule_id: str) -> dict[str, Any] | None:
        return self._fetch_one(
            "select * from classification_rules where id = %s and user_id = %s",
            (rule_id, user_id),
        )

    def create_classification_rule(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_profile(user_id)
        return self._insert(
            "classification_rules",
            {
                "id": payload.get("id") or str(uuid4()),
                "user_id": user_id,
                "created_at": datetime.now(timezone.utc),
                **payload,
            },
        )

    def update_classification_rule(self, user_id: str, rule_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        return self._update(
            "classification_rules",
            payload,
            "id = %s and user_id = %s",
            (rule_id, user_id),
        )

    def delete_classification_rule(self, user_id: str, rule_id: str) -> dict[str, Any] | None:
        return self.update_classification_rule(user_id, rule_id, {"status": "inactive"})

    def category_exists(self, category_id: str, user_id: str | None = None) -> bool:
        if user_id is None:
            result = self._fetch_one("select 1 as exists from categories where id = %s and status = 'active'", (category_id,))
        else:
            result = self._fetch_one(
                "select 1 as exists from categories where id = %s and status = 'active' and (user_id is null or user_id = %s)",
                (category_id, user_id),
            )
        return result is not None

    def category_name(self, category_id: str | None) -> str | None:
        if not category_id:
            return None
        item = self._fetch_one("select name from categories where id = %s and status = 'active'", (category_id,))
        return item["name"] if item else None

    def match_classification_rule(
        self,
        user_id: str,
        description: str,
        original_description: str | None,
        transaction_type: str | None,
        amount: Any = None,
        external_source: str | None = None,
        category_id: str | None = None,
    ) -> dict[str, Any] | None:
        rules = [
            rule
            for rule in self.list_classification_rules(user_id)
            if rule.get("status") == "active"
            and (rule.get("transaction_type") is None or rule.get("transaction_type") == transaction_type)
        ]
        candidates: list[dict[str, Any]] = []
        description_text = description.upper()
        original_text = (original_description or "").upper()
        canonical_text = self._classification_payee_text(user_id, description, original_description)
        for rule in rules:
            if rule.get("conditions") and rule.get("actions"):
                matched_rule = self._match_structured_classification_rule(
                    rule,
                    description,
                    original_description,
                    transaction_type,
                    canonical_text,
                    amount=amount,
                    external_source=external_source,
                    category_id=category_id,
                )
                if matched_rule:
                    candidates.append(matched_rule)
                continue
            keyword = rule["keyword"].upper()
            scope = rule.get("match_scope", "both")
            haystacks = []
            if scope in ("description", "both"):
                haystacks.append(description_text)
            if scope in ("original_description", "both"):
                haystacks.append(original_text)
            if canonical_text:
                haystacks.append(canonical_text.upper())
            if any(keyword in haystack for haystack in haystacks):
                candidates.append(rule)
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (item.get("priority", 0), item.get("created_at", "")), reverse=True)[0]

    def _classification_payee_text(self, user_id: str, description: str, original_description: str | None) -> str:
        list_aliases = getattr(self, "list_payee_aliases", None)
        if not list_aliases:
            return ""
        combined = f"{description} {original_description or ''}"
        normalized = " ".join(combined.lower().split())
        matches = [
            str(alias.get("canonical_name") or "")
            for alias in list_aliases(user_id)
            if alias.get("normalized_alias") and str(alias["normalized_alias"]).lower() in normalized
        ]
        return " ".join(matches)

    def _match_structured_classification_rule(
        self,
        rule: dict[str, Any],
        description: str,
        original_description: str | None,
        transaction_type: str | None,
        canonical_text: str,
        amount: Any = None,
        external_source: str | None = None,
        category_id: str | None = None,
    ) -> dict[str, Any] | None:
        result = evaluate_structured_rule(
            rule,
            {
                "description": description,
                "original_description": original_description,
                "normalized_description": " ".join(description.lower().split()),
                "amount": amount,
                "category_id": category_id,
                "external_source": external_source,
                "payee": canonical_text,
                "type": transaction_type,
            },
        )
        if not result.matched:
            return None
        category_id = rule.get("category_id")
        for action in result.actions:
            if action.get("type") == "set_category":
                category_id = action.get("category_id")
                break
        if not category_id:
            return None
        return {**rule, "category_id": category_id}
