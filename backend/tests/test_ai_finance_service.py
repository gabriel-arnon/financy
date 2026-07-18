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


def test_ai_finance_overview_suggests_new_category_for_generic_recurring_group() -> None:
    response = AiFinanceService(FakeFinanceRepository()).overview("user-1")

    assert response.suggested_categories
    suggestion = response.suggested_categories[0]
    assert suggestion.name == "Petz"
    assert suggestion.type == "expense"
    assert suggestion.match_count == 2
    assert "PETZ LOJA" in suggestion.sample_descriptions
