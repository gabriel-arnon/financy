from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.repositories.local_json import LocalJsonRepository


DEMO_ACCOUNT_NAME = "Conta exemplo"
DEMO_CARD_NAME = "Cartao exemplo"


def _find_by_name(items: list[dict], name: str) -> dict | None:
    normalized = name.strip().lower()
    return next((item for item in items if str(item.get("name", "")).strip().lower() == normalized), None)


def seed_minimal(repository: LocalJsonRepository) -> dict[str, int]:
    categories = repository.categories()
    rules = repository.list_classification_rules(settings.dev_user_id)
    return {
        "categories": len(categories),
        "classification_rules": len(rules),
    }


def seed_demo_data(repository: LocalJsonRepository) -> dict[str, str]:
    user_id = settings.dev_user_id
    account = _find_by_name(repository.list_accounts(user_id), DEMO_ACCOUNT_NAME)
    if account is None:
        account = repository.create_account(
            user_id,
            {
                "name": DEMO_ACCOUNT_NAME,
                "institution": "Banco exemplo",
                "agency": None,
                "account_number": None,
                "type": "checking",
                "balance": str(Decimal("0.00")),
                "status": "active",
            },
        )

    card = _find_by_name(repository.list_cards(user_id), DEMO_CARD_NAME)
    if card is None:
        card = repository.create_card(
            user_id,
            {
                "account_id": account["id"],
                "name": DEMO_CARD_NAME,
                "institution": "Banco exemplo",
                "brand": "Visa",
                "last_digits": "0000",
                "limit_amount": str(Decimal("1000.00")),
                "closing_day": 20,
                "due_day": 10,
                "status": "active",
            },
        )

    return {
        "account_id": account["id"],
        "card_id": card["id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Financy local development data.")
    parser.add_argument(
        "--with-demo-data",
        action="store_true",
        help="Create one demo account and one demo card if they do not already exist.",
    )
    args = parser.parse_args()

    repository = LocalJsonRepository(settings.upload_dir)
    minimal = seed_minimal(repository)

    print("Minimal seed completed.")
    print(f"- upload_dir: {settings.upload_dir}")
    print(f"- categories: {minimal['categories']}")
    print(f"- classification_rules: {minimal['classification_rules']}")

    if args.with_demo_data:
        demo = seed_demo_data(repository)
        print("Demo data ensured.")
        print(f"- account_id: {demo['account_id']}")
        print(f"- card_id: {demo['card_id']}")


if __name__ == "__main__":
    main()
