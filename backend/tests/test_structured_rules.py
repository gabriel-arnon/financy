from app.services.structured_rules import evaluate_structured_rule, legacy_keyword_rule_to_structured


def transaction(**overrides):
    return {
        "amount": "120.50",
        "category_id": None,
        "description": "OPENAI CHATGPT ASSINATURA",
        "external_source": "open_finance",
        "normalized_description": "openai chatgpt assinatura",
        "original_description": "OPENAI *CHATGPT 123",
        "payee": "OpenAI",
        "type": "expense",
        **overrides,
    }


def test_structured_rule_matches_contains_and_amount_condition() -> None:
    rule = {
        "conditions": [
            {"field": "description", "operator": "contains", "value": "openai"},
            {"field": "amount", "operator": "gt", "value": "100"},
        ],
        "actions": [{"type": "set_category", "category_id": "cat-assinaturas"}],
    }

    result = evaluate_structured_rule(rule, transaction())

    assert result.matched is True
    assert result.actions == [{"type": "set_category", "category_id": "cat-assinaturas"}]


def test_structured_rule_rejects_invalid_regex_without_matching() -> None:
    rule = {
        "conditions": [{"field": "description", "operator": "regex", "value": "("}],
        "actions": [{"type": "set_category", "category_id": "cat-assinaturas"}],
    }

    result = evaluate_structured_rule(rule, transaction())

    assert result.matched is False
    assert result.error == "structured_rule_invalid_condition"


def test_structured_rule_supports_payee_action_and_ignores_non_matching_type() -> None:
    rule = {
        "conditions": [
            {"field": "payee", "operator": "equals", "value": "OpenAI"},
            {"field": "type", "operator": "equals", "value": "income"},
        ],
        "actions": [{"type": "set_payee", "payee_id": "payee-openai"}],
    }

    result = evaluate_structured_rule(rule, transaction())

    assert result.matched is False
    assert result.error is None


def test_legacy_keyword_rule_can_be_represented_as_structured_rule() -> None:
    structured = legacy_keyword_rule_to_structured(
        {
            "keyword": "OPENAI",
            "category_id": "cat-assinaturas",
            "transaction_type": "expense",
            "match_scope": "description",
            "priority": 200,
            "status": "active",
        }
    )

    result = evaluate_structured_rule(structured, transaction())

    assert result.matched is True
    assert result.actions[0] == {"type": "set_category", "category_id": "cat-assinaturas"}
    assert structured["priority"] == 200


def test_legacy_keyword_rule_with_both_scope_matches_either_description_field() -> None:
    structured = legacy_keyword_rule_to_structured(
        {
            "keyword": "OPENAI",
            "category_id": "cat-assinaturas",
            "transaction_type": None,
            "match_scope": "both",
        }
    )

    result = evaluate_structured_rule(
        structured,
        transaction(description="SERVICO ASSINATURA", original_description="OPENAI *CHATGPT 123"),
    )

    assert result.matched is True
    assert structured["conditions"][0] == {"field": "combined_description", "operator": "contains", "value": "OPENAI"}
