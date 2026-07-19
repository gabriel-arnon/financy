from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import repository
from app.models.enums import TransactionType
from app.repositories.local_json import LocalJsonRepository
from app.services.classification_rule_preview_service import ClassificationRulePreviewService
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


def test_structured_classification_rule_api_persists_contract_and_validates_action_category() -> None:
    client = TestClient(app)
    category_id = client.get("/categories").json()[0]["id"]
    keyword = f"STRUCTURED_{uuid4().hex[:8]}"

    invalid = client.post(
        "/classification-rules",
        json={
            "keyword": f"{keyword}_INVALID",
            "category_id": category_id,
            "priority": 100,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
            "conditions": [{"field": "description", "operator": "contains", "value": "openai"}],
            "actions": [{"type": "set_category", "category_id": "00000000-0000-4000-8000-000000000000"}],
            "rule_version": 2,
        },
    )
    assert invalid.status_code == 400

    created = client.post(
        "/classification-rules",
        json={
            "keyword": keyword,
            "category_id": category_id,
            "transaction_type": "expense",
            "priority": 210,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
            "conditions": [
                {"field": "description", "operator": "contains", "value": "openai"},
                {"field": "amount", "operator": "gt", "value": "50"},
            ],
            "condition_logic": "all",
            "actions": [{"type": "set_category", "category_id": category_id}],
            "rule_version": 2,
        },
    )

    assert created.status_code == 200
    body = created.json()
    assert body["conditions"][0]["field"] == "description"
    assert body["condition_logic"] == "all"
    assert body["actions"][0] == {"type": "set_category", "category_id": category_id, "payee_id": None}
    assert body["rule_version"] == 2


def test_classification_rule_api_rejects_duplicate_active_rule() -> None:
    client = TestClient(app)
    category_id = client.get("/categories").json()[0]["id"]
    keyword = f"DUPLICATE_{uuid4().hex[:8]}"
    payload = {
        "keyword": keyword,
        "category_id": category_id,
        "transaction_type": "expense",
        "priority": 100,
        "status": "active",
        "match_scope": "both",
        "auto_created": False,
    }

    created = client.post("/classification-rules", json=payload)
    duplicate = client.post("/classification-rules", json=payload)

    assert created.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "classification_rule_already_exists"


def test_classification_rule_preview_endpoint_returns_impact_without_creating_rule() -> None:
    client = TestClient(app)
    category_id = client.get("/categories").json()[0]["id"]
    keyword = f"PREVIEW_{uuid4().hex[:8]}"
    source_file = repository.create_import_file(
        {
            "user_id": USER_ID,
            "filename": f"{keyword}.csv",
            "content_type": "text/csv",
            "storage_path": f"local/{keyword}.csv",
            "size_bytes": 10,
        }
    )

    created_transaction = client.post(
        "/transactions",
        json={
            "source_file_id": source_file["id"],
            "transaction_date": "2026-07-19",
            "description": f"{keyword} ASSINATURA",
            "original_description": f"{keyword} RAW",
            "amount": "42.90",
            "type": "expense",
            "category_id": None,
            "status": "confirmed",
        },
    )
    assert created_transaction.status_code == 200

    payload = {
        "keyword": keyword,
        "category_id": category_id,
        "transaction_type": "expense",
        "priority": 100,
        "status": "active",
        "match_scope": "both",
        "auto_created": False,
    }
    preview = client.post("/classification-rules/preview", json=payload)

    assert preview.status_code == 200
    body = preview.json()
    assert body["matched_count"] >= 1
    assert body["changed_count"] >= 1
    assert body["samples"][0]["proposed_category_id"] == category_id
    assert body["samples"][0]["transaction_id"] == created_transaction.json()["id"]
    assert keyword not in {rule["keyword"] for rule in client.get("/classification-rules").json()}


def test_classification_rule_preview_service_counts_unchanged_and_changed_matches(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    current_category_id = _category_id(repo, "Outros")
    proposed_category_id = _category_id(repo, "Assinaturas")
    service = TransactionService(repo)
    source_file = repo.create_import_file(
        {
            "user_id": USER_ID,
            "filename": "preview.csv",
            "content_type": "text/csv",
            "storage_path": "local/preview.csv",
            "size_bytes": 10,
        }
    )
    service.create(
        USER_ID,
        payload_dict={
            "source_file_id": source_file["id"],
            "transaction_date": "2026-07-01",
            "description": "OPENAI CHATGPT",
            "original_description": "OPENAI CHATGPT",
            "amount": "100.00",
            "type": "expense",
            "category_id": current_category_id,
            "status": "confirmed",
        },
    )
    service.create(
        USER_ID,
        payload_dict={
            "source_file_id": source_file["id"],
            "transaction_date": "2026-07-02",
            "description": "OPENAI API",
            "original_description": "OPENAI API",
            "amount": "50.00",
            "type": "expense",
            "category_id": proposed_category_id,
            "status": "confirmed",
        },
    )

    preview = ClassificationRulePreviewService(repo).preview(
        USER_ID,
        {
            "keyword": "OPENAI",
            "category_id": proposed_category_id,
            "transaction_type": "expense",
            "match_scope": "both",
        },
    )

    assert preview.matched_count == 2
    assert preview.changed_count == 1
    assert preview.unchanged_count == 1
    assert len(preview.samples) == 2


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


def test_rule_matching_uses_confirmed_payee_alias_without_changing_description(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    category_id = _category_id(repo, "Assinaturas")
    payee = repo.create_payee(USER_ID, {"canonical_name": "Netflix"})
    repo.create_payee_alias(USER_ID, payee["id"], {"alias": "MPNF", "normalized_alias": "mpnf"})
    repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "NETFLIX",
            "category_id": category_id,
            "transaction_type": "expense",
            "priority": 100,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
        },
    )

    matched = repo.match_classification_rule(USER_ID, "MPNF 123456", "MPNF 123456", "expense")

    assert matched is not None
    assert matched["category_id"] == category_id


def test_structured_rule_matching_uses_priority_and_recent_tiebreak(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    category_a = _category_id(repo, "Assinaturas")
    category_b = _category_id(repo, "Outros")
    repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "OPENAI_STRUCTURED_A",
            "category_id": category_a,
            "transaction_type": "expense",
            "priority": 150,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
            "conditions": [{"field": "description", "operator": "contains", "value": "openai"}],
            "actions": [{"type": "set_category", "category_id": category_a}],
            "rule_version": 2,
        },
    )
    newer = repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "OPENAI_STRUCTURED_B",
            "category_id": category_b,
            "transaction_type": "expense",
            "priority": 150,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
            "conditions": [{"field": "description", "operator": "contains", "value": "openai"}],
            "actions": [{"type": "set_category", "category_id": category_b}],
            "rule_version": 2,
        },
    )

    matched = repo.match_classification_rule(USER_ID, "OPENAI CHATGPT", "OPENAI CHATGPT", "expense")

    assert matched is not None
    assert matched["id"] == newer["id"]
    assert matched["category_id"] == category_b


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


def test_import_preview_applies_structured_rule(tmp_path: Path) -> None:
    repo = LocalJsonRepository(tmp_path)
    category_id = _category_id(repo, "Assinaturas")
    repo.create_classification_rule(
        USER_ID,
        {
            "keyword": "OPENAI_STRUCTURED",
            "category_id": category_id,
            "transaction_type": "expense",
            "priority": 250,
            "status": "active",
            "match_scope": "both",
            "auto_created": False,
            "conditions": [
                {"field": "description", "operator": "contains", "value": "openai"},
                {"field": "amount", "operator": "gt", "value": "50"},
            ],
            "actions": [{"type": "set_category", "category_id": category_id}],
            "rule_version": 2,
        },
    )

    item = ImportService(repo, tmp_path)._apply_classification(
        USER_ID,
        {
            "description": "OPENAI CHATGPT",
            "original_description": "OPENAI CHATGPT",
            "amount": "100.00",
            "type": "expense",
            "suggested_category": None,
            "needs_review": False,
        },
    )

    assert item["category_id"] == category_id
    assert item["classification_rule_id"]
    assert item["classification_label"].startswith("Regra: OPENAI_STRUCTURED")


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
    account = repo.create_account(
        USER_ID,
        {
            "name": "Conta Teste",
            "institution": "Banco Teste",
            "type": "checking",
            "balance": "0",
            "status": "active",
        },
    )
    created = service.create(
        USER_ID,
        payload_dict={
            "account_id": account["id"],
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
