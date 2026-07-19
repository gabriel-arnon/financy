from app.services.ai_finance_service import AiFinanceService


class FakeFinanceRepository:
    def categories(self, user_id: str | None = None):
        return [
            {"id": "cat-assinaturas", "name": "Assinaturas", "type": "expense", "status": "active"},
            {"id": "cat-mercado", "name": "Mercado", "type": "expense", "status": "active"},
            {"id": "cat-outros", "name": "Outros", "type": "both", "status": "active"},
        ]

    def list_transactions(self, user_id: str):
        return [
            {
                "id": "tx-1",
                "transaction_date": "2026-07-01",
                "description": "OPENAI CHATGPT",
                "original_description": "OPENAI CHATGPT",
                "amount": "100.00",
                "type": "expense",
                "category_id": "cat-assinaturas",
                "external_source": "open_finance",
            },
            {
                "id": "tx-2",
                "transaction_date": "2026-07-10",
                "description": "SPOTIFY",
                "original_description": "SPOTIFY",
                "amount": "30.30",
                "type": "expense",
                "category_id": "cat-assinaturas",
            },
            {
                "id": "tx-3",
                "transaction_date": "2026-06-10",
                "description": "MERCADO TESTE",
                "original_description": "MERCADO TESTE",
                "amount": "55.00",
                "type": "expense",
                "category_id": "cat-mercado",
            },
            {
                "id": "tx-4",
                "transaction_date": "2026-07-11",
                "description": "PETZ LOJA",
                "original_description": "PETZ LOJA",
                "amount": "80.00",
                "type": "expense",
                "category_id": "cat-outros",
            },
            {
                "id": "tx-5",
                "transaction_date": "2026-07-12",
                "description": "PETZ BANHO",
                "original_description": "PETZ BANHO",
                "amount": "95.00",
                "type": "expense",
                "category_id": "cat-outros",
            },
        ]

    def list_classification_rules(self, user_id: str):
        return []

    def list_payee_aliases(self, user_id: str):
        return []


def test_ai_finance_answer_returns_structured_cta() -> None:
    response = AiFinanceService(FakeFinanceRepository()).answer(
        "user-1",
        "quanto gastei com assinaturas esse mes",
    )

    assert response.answer == "Encontrei 2 transacoes neste mes, no valor total de R$ 130,30."
    assert response.message == response.answer
    assert response.matched_count == 2
    assert response.total_amount == "130.30"
    assert response.summary is not None
    assert response.summary.currency == "BRL"
    assert response.cta is not None
    assert response.cta.route == "/transactions"
    assert response.cta.query == {
        "type": "expense",
        "category_id": "cat-assinaturas",
        "start_date": "2026-07-01",
        "end_date": "2026-07-31",
    }


def test_ai_finance_answer_keeps_textual_fallback_fields() -> None:
    response = AiFinanceService(FakeFinanceRepository()).answer("user-1", "quanto")

    assert response.answer
    assert response.matched_count == 5
    assert response.total_amount == "360.30"
    assert isinstance(response.filters, list)
    assert response.message == response.answer


def test_ai_finance_overview_includes_open_finance_transactions() -> None:
    response = AiFinanceService(FakeFinanceRepository()).overview("user-1")

    assert "305.30" in response.summary


def test_ai_finance_overview_compares_previous_period() -> None:
    response = AiFinanceService(FakeFinanceRepository()).overview("user-1")

    comparison = next((insight for insight in response.insights if insight.title == "Comparacao com periodo anterior"), None)

    assert comparison is not None
    assert "250.30" in comparison.description
    assert "piorou" in comparison.description
    assert comparison.severity == "warning"


def test_ai_finance_overview_suggests_new_category_for_generic_recurring_group() -> None:
    response = AiFinanceService(FakeFinanceRepository()).overview("user-1")

    assert response.suggested_categories
    suggestion = response.suggested_categories[0]
    assert suggestion.name == "Petz"
    assert suggestion.type == "expense"
    assert suggestion.match_count == 2
    assert "PETZ LOJA" in suggestion.sample_descriptions


def test_ai_finance_overview_suggests_structured_rule_with_human_confirmation_payload() -> None:
    class RuleSuggestionRepository(FakeFinanceRepository):
        def list_transactions(self, user_id: str):
            return [
                {
                    "id": "rule-1",
                    "transaction_date": "2026-07-01",
                    "description": "NETFLIX ASSINATURA",
                    "original_description": "NETFLIX ASSINATURA",
                    "amount": "39.90",
                    "type": "expense",
                    "category_id": "cat-assinaturas",
                },
                {
                    "id": "rule-2",
                    "transaction_date": "2026-07-10",
                    "description": "NETFLIX ASSINATURA JULHO",
                    "original_description": "NETFLIX ASSINATURA JULHO",
                    "amount": "39.90",
                    "type": "expense",
                    "category_id": "cat-assinaturas",
                },
            ]

    response = AiFinanceService(RuleSuggestionRepository()).overview("user-1")

    suggestion = next(rule for rule in response.suggested_rules if rule.keyword == "netflix assinatura")
    assert suggestion.category_id == "cat-assinaturas"
    assert suggestion.match_count == 2
    assert suggestion.conditions == [{"field": "combined_description", "operator": "contains", "value": "netflix assinatura"}]
    assert suggestion.actions == [{"type": "set_category", "category_id": "cat-assinaturas"}]
    assert suggestion.rule_version == 2


def test_ai_finance_overview_suggests_payee_aliases_for_noisy_descriptions() -> None:
    class PayeeRepository(FakeFinanceRepository):
        def list_transactions(self, user_id: str):
            return [
                {
                    "id": "pix-1",
                    "transaction_date": "2026-07-01",
                    "description": "PIX MERCEARIA BOA",
                    "original_description": "PIX MERCEARIA BOA",
                    "amount": "80.00",
                    "type": "expense",
                    "category_id": "cat-mercado",
                },
                {
                    "id": "pix-2",
                    "transaction_date": "2026-07-08",
                    "description": "MERCEARIA BOA LTDA 123456",
                    "original_description": "MERCEARIA BOA LTDA 123456",
                    "amount": "91.00",
                    "type": "expense",
                    "category_id": "cat-mercado",
                },
                {
                    "id": "acquirer-1",
                    "transaction_date": "2026-07-10",
                    "description": "PAGSEGURO UBER TRIP",
                    "original_description": "PAGSEGURO UBER TRIP",
                    "amount": "21.00",
                    "type": "expense",
                    "category_id": "cat-outros",
                },
                {
                    "id": "acquirer-2",
                    "transaction_date": "2026-07-11",
                    "description": "UBER TRIP HELP.UBER.COM",
                    "original_description": "UBER TRIP HELP.UBER.COM",
                    "amount": "22.00",
                    "type": "expense",
                    "category_id": "cat-outros",
                },
                {
                    "id": "marketplace-1",
                    "transaction_date": "2026-07-12",
                    "description": "MERCADOPAGO NETFLIX 123",
                    "original_description": "MERCADOPAGO NETFLIX 123",
                    "amount": "39.90",
                    "type": "expense",
                    "category_id": "cat-assinaturas",
                },
                {
                    "id": "marketplace-2",
                    "transaction_date": "2026-07-13",
                    "description": "NETFLIX.COM ASSINATURA",
                    "original_description": "NETFLIX.COM ASSINATURA",
                    "amount": "39.90",
                    "type": "expense",
                    "category_id": "cat-assinaturas",
                },
            ]

    response = AiFinanceService(PayeeRepository()).overview("user-1")
    suggestions = {item.canonical_name: item for item in response.suggested_payee_aliases}

    assert "Mercearia Boa" in suggestions
    assert "Uber Trip" in suggestions
    assert "Netflix" in suggestions
    assert "PIX MERCEARIA BOA" in suggestions["Mercearia Boa"].aliases
    assert suggestions["Netflix"].match_count == 2


def test_ai_finance_answer_uses_confirmed_payee_aliases_without_changing_descriptions() -> None:
    class AliasRepository(FakeFinanceRepository):
        def list_payee_aliases(self, user_id: str):
            return [
                {
                    "alias": "mercadopago netflix",
                    "normalized_alias": "mercadopago netflix",
                    "canonical_name": "Netflix",
                }
            ]

        def list_transactions(self, user_id: str):
            return [
                {
                    "id": "tx-netflix",
                    "transaction_date": "2026-07-02",
                    "description": "MERCADOPAGO NETFLIX 123",
                    "original_description": "MERCADOPAGO NETFLIX 123",
                    "amount": "39.90",
                    "type": "expense",
                    "category_id": "cat-assinaturas",
                }
            ]

    repository = AliasRepository()
    response = AiFinanceService(repository).answer("user-1", "quanto gastei com netflix esse mes")

    assert response.matched_count == 1
    assert response.total_amount == "39.90"
    assert repository.list_transactions("user-1")[0]["original_description"] == "MERCADOPAGO NETFLIX 123"
