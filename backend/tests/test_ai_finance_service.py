from app.services.ai_finance_service import AiFinanceService


class FakeFinanceRepository:
    def categories(self, user_id: str | None = None):
        return [
            {"id": "cat-assinaturas", "name": "Assinaturas", "type": "expense", "status": "active"},
            {"id": "cat-mercado", "name": "Mercado", "type": "expense", "status": "active"},
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
        ]


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
    assert response.matched_count == 3
    assert response.total_amount == "185.30"
    assert isinstance(response.filters, list)
    assert response.message == response.answer
