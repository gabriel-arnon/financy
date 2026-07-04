from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import TransactionType
from app.repositories.local_json import LocalJsonRepository
from app.schemas.transactions import TransactionUpdate
from app.services.import_service import ImportService
from app.services.transaction_service import TransactionService


USER_ID = "00000000-0000-4000-8000-000000000001"


def _category_id(repo: LocalJsonRepository, name: str) -> str:
    return next(category["id"] for category in repo.categories() if category["name"] == name)


def test_classification_rules_crud_and_validation() -> None:
    client = TestClient(app)
    category_id = client.get("/categories").json()[0]["id"]

    invalid = client.post(
        "/classification-rules",
        json={
            "keyword": "TESTE",
            "category_id": "00000000-0000-4000-8000-000000000000",
            "priority": 100,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
        },
    )
    assert invalid.status_code == 400

    created = client.post(
        "/classification-rules",
        json={
            "keyword": "teste",
            "category_id": category_id,
            "transaction_type": "expense",
            "priority": 150,
            "status": "active",
            "match_scope": "description",
            "auto_created": False,
        },
    )
    assert created.status_code == 200
    rule = created.json()
    assert rule["keyword"] == "TESTE"

    updated = client.put(f"/classification-rules/{rule['id']}", json={"priority": 151})
    assert updated.status_code == 200
    assert updated.json()["priority"] == 151

    deleted = client.delete(f"/classification-rules/{rule['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "inactive"

    listed = client.get("/classification-rules")
    assert listed.status_code == 200
    assert rule["id"] not in {item["id"] for item in listed.json()}


def test_initial_rules_are_seeded_even_when_custom_rule_exists(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    category_id = _category_id(repo, "Outros")
    repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "CUSTOM",
            "category_id": category_id,
            "transaction_type": "expense",
            "priority": 100,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
        },
    )

    keywords = {rule["keyword"] for rule in repo.list_classification_rules(USER_ID)}

    assert {"OPENAI", "MERCADOLIVRE", "IFOOD", "IFD", "KAMPAI", "POSTO", "ANUIDADE", "CUSTOM"}.issubset(keywords)


def test_rule_matching_scope_priority_and_recent_tiebreak(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    category_a = _category_id(repo, "Assinaturas")
    category_b = _category_id(repo, "Outros")

    repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "OPENAI",
            "category_id": category_a,
            "transaction_type": "expense",
            "priority": 200,
            "status": "active",
            "match_scope": "original_description",
            "auto_created": False,
        },
    )
    lower_priority = repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "OPENAI",
            "category_id": category_b,
            "transaction_type": "expense",
            "priority": 100,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
        },
    )

    matched = repo.match_classification_rule(USER_ID, "Servico editado", "OPENAI CHATGPT", "expense")
    assert matched is not None
    assert matched["category_id"] == category_a

    repo.update_classification_rule(USER_ID, lower_priority["id"], {"priority": 200})
    matched_tie = repo.match_classification_rule(USER_ID, "OPENAI editado", "OPENAI CHATGPT", "expense")
    assert matched_tie is not None
    assert matched_tie["id"] == lower_priority["id"]


def test_import_preview_applies_rule_and_marks_suggestion_conflict(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    category_id = _category_id(repo, "Assinaturas")
    repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "OPENAI",
            "category_id": category_id,
            "transaction_type": "expense",
            "priority": 100,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
        },
    )

    item = ImportService(repo, tmp_path)._apply_classification(
        USER_ID,
        {
            "description": "OPENAI CHATGPT",
            "original_description": "OPENAI CHATGPT",
            "type": "expense",
            "suggested_category": "Serviços",
            "needs_review": False,
        },
    )

    assert item["category_id"] == category_id
    assert item["classification_label"].startswith("Regra: OPENAI")
    assert item["suggested_category"] == "Serviços"
    assert item["needs_review"] is True


def test_transaction_update_classification_respects_manual_category(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    category_id = _category_id(repo, "Assinaturas")
    repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "OPENAI",
            "category_id": category_id,
            "transaction_type": TransactionType.expense.value,
            "priority": 100,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
        },
    )
    service = TransactionService(repo)
    created = service.create(
        USER_ID,
        payload_dict={
            "transaction_date": "2026-06-01",
            "description": "SEM CATEGORIA",
            "original_description": "SEM CATEGORIA",
            "amount": "10.00",
            "type": "expense",
            "category_id": None,
            "status": "confirmed",
        },
    )

    assert created is not None

    updated = service.update(USER_ID, created["id"], payload=TransactionUpdate(description="OPENAI CHATGPT"))
    assert updated.category_id == category_id

    cleared = service.update(
        USER_ID,
        created["id"],
        payload=TransactionUpdate(description="OPENAI CHATGPT", category_id=None),
    )
    assert cleared.category_id is None
