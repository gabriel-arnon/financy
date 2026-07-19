from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.parsers.utils import normalize_description


ALLOWED_FIELDS = {
    "amount",
    "category_id",
    "combined_description",
    "description",
    "external_source",
    "normalized_description",
    "original_description",
    "payee",
    "type",
}
ALLOWED_OPERATORS = {"contains", "starts_with", "equals", "regex", "gt", "lt"}
ALLOWED_ACTIONS = {"set_category", "set_payee", "ignore_from_reports"}
ALLOWED_CONDITION_LOGIC = {"all", "any"}
MAX_REGEX_LENGTH = 128


@dataclass(frozen=True)
class StructuredRuleResult:
    matched: bool
    actions: list[dict[str, Any]]
    error: str | None = None


def evaluate_structured_rule(rule: dict[str, Any], transaction: dict[str, Any]) -> StructuredRuleResult:
    conditions = rule.get("conditions") if isinstance(rule.get("conditions"), list) else []
    actions = rule.get("actions") if isinstance(rule.get("actions"), list) else []
    condition_logic = rule.get("condition_logic") or "all"
    if not conditions:
        return StructuredRuleResult(matched=False, actions=[], error="structured_rule_without_conditions")
    if condition_logic not in ALLOWED_CONDITION_LOGIC:
        return StructuredRuleResult(matched=False, actions=[], error="structured_rule_invalid_condition_logic")
    if not _actions_are_valid(actions):
        return StructuredRuleResult(matched=False, actions=[], error="structured_rule_invalid_actions")

    has_match = False
    for condition in conditions:
        valid, matched = _evaluate_condition(condition, transaction)
        if not valid:
            return StructuredRuleResult(matched=False, actions=[], error="structured_rule_invalid_condition")
        if condition_logic == "all" and not matched:
            return StructuredRuleResult(matched=False, actions=[])
        if condition_logic == "any" and matched:
            has_match = True
    if condition_logic == "any" and not has_match:
        return StructuredRuleResult(matched=False, actions=[])
    return StructuredRuleResult(matched=True, actions=actions)


def legacy_keyword_rule_to_structured(rule: dict[str, Any]) -> dict[str, Any]:
    keyword = str(rule.get("keyword") or "").strip()
    conditions = []
    scope = rule.get("match_scope") or "both"
    if scope in {"description", "both"}:
        field = "combined_description" if scope == "both" else "description"
        conditions.append({"field": field, "operator": "contains", "value": keyword})
    elif scope == "original_description":
        conditions.append({"field": "original_description", "operator": "contains", "value": keyword})
    if rule.get("transaction_type"):
        conditions.append({"field": "type", "operator": "equals", "value": rule["transaction_type"]})
    return {
        "conditions": conditions,
        "actions": [{"type": "set_category", "category_id": rule.get("category_id")}],
        "priority": rule.get("priority", 100),
        "status": rule.get("status", "active"),
    }


def _actions_are_valid(actions: list[Any]) -> bool:
    if not actions:
        return False
    for action in actions:
        if not isinstance(action, dict) or action.get("type") not in ALLOWED_ACTIONS:
            return False
        if action["type"] == "set_category" and not action.get("category_id"):
            return False
        if action["type"] == "set_payee" and not action.get("payee_id"):
            return False
    return True


def _evaluate_condition(condition: Any, transaction: dict[str, Any]) -> tuple[bool, bool]:
    if not isinstance(condition, dict):
        return False, False
    field = str(condition.get("field") or "")
    operator = str(condition.get("operator") or "")
    if field not in ALLOWED_FIELDS or operator not in ALLOWED_OPERATORS:
        return False, False
    actual = _field_value(field, transaction)
    expected = condition.get("value")
    if operator in {"gt", "lt"}:
        return _compare_decimal(actual, expected, operator)
    actual_text = _comparison_text(actual)
    expected_text = _comparison_text(expected)
    if operator == "contains":
        return True, expected_text in actual_text
    if operator == "starts_with":
        return True, actual_text.startswith(expected_text)
    if operator == "equals":
        return True, actual_text == expected_text
    if operator == "regex":
        return _match_regex(expected_text, actual_text)
    return False, False


def _field_value(field: str, transaction: dict[str, Any]) -> Any:
    if field == "combined_description":
        return f"{transaction.get('description') or ''} {transaction.get('original_description') or ''}"
    if field == "normalized_description":
        return transaction.get("normalized_description") or normalize_description(str(transaction.get("description") or ""))
    return transaction.get(field)


def _comparison_text(value: Any) -> str:
    return normalize_description(str(value or "")).lower()


def _compare_decimal(actual: Any, expected: Any, operator: str) -> tuple[bool, bool]:
    try:
        actual_decimal = Decimal(str(actual))
        expected_decimal = Decimal(str(expected))
    except (InvalidOperation, TypeError, ValueError):
        return False, False
    if operator == "gt":
        return True, actual_decimal > expected_decimal
    return True, actual_decimal < expected_decimal


def _match_regex(pattern: str, value: str) -> tuple[bool, bool]:
    if not pattern or len(pattern) > MAX_REGEX_LENGTH:
        return False, False
    try:
        return True, re.search(pattern, value, flags=re.IGNORECASE) is not None
    except re.error:
        return False, False
