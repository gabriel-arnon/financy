from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.schemas.ai_finance import (
    AiCategorySuggestion,
    AiFinanceQuestionCta,
    AiFinanceInsight,
    AiFinanceOverview,
    AiFinanceQuestionResponse,
    AiFinanceQuestionSummary,
    AiRecurrenceSuggestion,
    AiRenameSuggestion,
    AiSuggestedCategory,
    AiSuggestedPayeeAlias,
    AiSuggestedRule,
)


INCOME_TYPES = {"income", "refund"}
EXPENSE_TYPES = {"expense", "payment"}
STOPWORDS = {
    "compra",
    "pagamento",
    "credito",
    "debito",
    "cartao",
    "pix",
    "ted",
    "doc",
    "transferencia",
    "mercado",
    "loja",
    "online",
    "com",
    "pag",
    "pagto",
    "superdigital",
    "internet",
}
GENERIC_CATEGORY_NAMES = {"outros", "outras", "diversos", "diversas", "sem categoria", "geral"}
PAYEE_NOISE_WORDS = STOPWORDS | {
    "assinatura",
    "brasil",
    "ecommerce",
    "marketplace",
    "mercadopago",
    "mp",
    "pagseguro",
    "pay",
    "recarga",
    "sa",
    "servico",
    "servicos",
    "shop",
}


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")


def _money_text(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def _brl_text(value: Decimal) -> str:
    formatted = f"{value.quantize(Decimal('0.01')):,.2f}"
    return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _normalize_description(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9À-ÿ ]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", cleaned)


def _keyword(description: str) -> str | None:
    words = [word for word in _normalize_description(description).split() if len(word) >= 4 and word not in STOPWORDS]
    if not words:
        return None
    return " ".join(words[:2])


def _pretty_description(description: str) -> str:
    cleaned = re.sub(r"\s+", " ", re.sub(r"[*_#;/\\|]+", " ", description)).strip()
    cleaned = re.sub(r"\b\d{6,}\b", "", cleaned).strip()
    return cleaned.title() if cleaned.isupper() else cleaned


def _alias_fingerprint(description: str) -> str | None:
    normalized = _normalize_description(description)
    normalized = re.sub(r"\b\d+\b", " ", normalized)
    words = [word for word in normalized.split() if len(word) >= 3 and word not in PAYEE_NOISE_WORDS]
    if not words:
        return None
    return " ".join(words[:2])


def _category_candidate_name(keyword: str) -> str:
    words = [word for word in keyword.split() if word and word not in STOPWORDS]
    return " ".join(words[:2]).title()


def _previous_month(value: date | None) -> date | None:
    if value is None:
        return None
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)


class AiFinanceService:
    def __init__(self, repository: Any):
        self.repository = repository

    def overview(self, user_id: str) -> AiFinanceOverview:
        transactions = self.repository.list_transactions(user_id)
        categories = self.repository.categories(user_id)
        rules = self.repository.list_classification_rules(user_id)
        payee_aliases = self._payee_aliases(user_id)
        category_by_id = {category["id"]: category for category in categories}
        transaction_dates = [parsed for item in transactions if (parsed := _parse_date(item.get("transaction_date")))]
        current_month = max(transaction_dates, default=None)
        month_transactions = self._month_transactions(transactions, current_month)
        previous_month_transactions = self._month_transactions(transactions, _previous_month(current_month))

        income_total = sum((_money(item.get("amount")) for item in month_transactions if item.get("type") in INCOME_TYPES), Decimal("0"))
        expense_total = sum((_money(item.get("amount")) for item in month_transactions if item.get("type") in EXPENSE_TYPES), Decimal("0"))
        net_total = income_total - expense_total

        insights = self._insights(month_transactions, previous_month_transactions, category_by_id, income_total, expense_total, net_total)
        return AiFinanceOverview(
            summary=(
                f"No período analisado, entradas somaram {_money_text(income_total)}, "
                f"saídas somaram {_money_text(expense_total)} e o resultado foi {_money_text(net_total)}."
            ),
            insights=insights,
            suggested_rules=self._suggest_rules(transactions, category_by_id, rules),
            suggested_categories=self._suggest_new_categories(transactions, category_by_id),
            suggested_payee_aliases=self._suggest_payee_aliases(transactions, payee_aliases),
            category_suggestions=self._suggest_categories(transactions, category_by_id),
            recurrence_suggestions=self._suggest_recurrences(transactions, payee_aliases),
            rename_suggestions=self._suggest_renames(transactions),
        )

    def _legacy_answer(self, user_id: str, question: str) -> AiFinanceQuestionResponse:
        transactions = self.repository.list_transactions(user_id)
        categories = self.repository.categories(user_id)
        category_by_id = {category["id"]: category for category in categories}
        normalized_question = _normalize_description(question)
        matched = transactions
        filters: list[str] = []

        if any(word in normalized_question for word in ["receita", "entrada", "ganhei", "recebi"]):
            matched = [item for item in matched if item.get("type") in INCOME_TYPES]
            filters.append("entradas")
        elif any(word in normalized_question for word in ["despesa", "gasto", "gastei", "saida", "saída"]):
            matched = [item for item in matched if item.get("type") in EXPENSE_TYPES]
            filters.append("saídas")

        matched_category = next(
            (category for category in categories if _normalize_description(category.get("name", "")) in normalized_question),
            None,
        )
        if matched_category:
            matched = [item for item in matched if item.get("category_id") == matched_category["id"]]
            filters.append(f"categoria {matched_category['name']}")

        month_number = self._question_month(normalized_question)
        if month_number:
            matched = [item for item in matched if (parsed := _parse_date(item.get("transaction_date"))) and parsed.month == month_number]
            filters.append(f"mês {month_number:02d}")

        total = sum((_money(item.get("amount")) for item in matched), Decimal("0"))
        if not filters:
            top_categories = self._top_expense_categories(matched, category_by_id, limit=3)
            if top_categories:
                description = ", ".join(f"{name}: {_money_text(amount)}" for name, amount in top_categories)
                return AiFinanceQuestionResponse(
                    answer=f"Encontrei {len(matched)} transações. Maiores grupos: {description}.",
                    matched_count=len(matched),
                    total_amount=_money_text(total),
                    filters=[],
                )

        return AiFinanceQuestionResponse(
            answer=f"Encontrei {len(matched)} transações para a pergunta. Total analisado: {_money_text(total)}.",
            matched_count=len(matched),
            total_amount=_money_text(total),
            filters=filters,
        )

    def answer(self, user_id: str, question: str) -> AiFinanceQuestionResponse:
        transactions = self.repository.list_transactions(user_id)
        categories = self.repository.categories(user_id)
        payee_aliases = self._payee_aliases(user_id)
        category_by_id = {category["id"]: category for category in categories}
        normalized_question = _normalize_description(question)
        matched = transactions
        filters: list[str] = []
        query: dict[str, str] = {}

        if any(word in normalized_question for word in ["receita", "entrada", "ganhei", "recebi"]):
            matched = [item for item in matched if item.get("type") in INCOME_TYPES]
            filters.append("entradas")
            query["type"] = "income"
        elif any(word in normalized_question for word in ["despesa", "gasto", "gastei", "saida"]):
            matched = [item for item in matched if item.get("type") in EXPENSE_TYPES]
            filters.append("saidas")
            query["type"] = "expense"

        matched_category = next(
            (category for category in categories if _normalize_description(category.get("name", "")) in normalized_question),
            None,
        )
        if matched_category:
            matched = [item for item in matched if item.get("category_id") == matched_category["id"]]
            filters.append(f"categoria {matched_category['name']}")
            query["category_id"] = matched_category["id"]
        else:
            keyword = self._question_keyword(normalized_question)
            if keyword:
                matched = [
                    item
                    for item in matched
                    if keyword in _normalize_description(self._canonical_description(item.get("description", ""), payee_aliases))
                    or keyword in _normalize_description(self._canonical_description(item.get("original_description", "") or "", payee_aliases))
                ]
                filters.append(keyword)
                query["q"] = keyword

        period = self._question_period(normalized_question, transactions)
        period_label = None
        if period:
            start, end, period_label = period
            matched = [
                item
                for item in matched
                if (parsed := _parse_date(item.get("transaction_date"))) and parsed >= start and parsed <= end
            ]
            filters.append(period_label)
            query["start_date"] = start.isoformat()
            query["end_date"] = end.isoformat()

        total = sum((_money(item.get("amount")) for item in matched), Decimal("0"))
        message = self._answer_message(len(matched), total, period_label)
        cta = AiFinanceQuestionCta(label="Ver transacoes", route="/transactions", query=query) if matched else None
        if not filters:
            top_categories = self._top_expense_categories(matched, category_by_id, limit=3)
            if top_categories:
                description = ", ".join(f"{name}: {_brl_text(amount)}" for name, amount in top_categories)
                fallback_message = f"Encontrei {len(matched)} transacoes. Maiores grupos: {description}."
                return AiFinanceQuestionResponse(
                    answer=fallback_message,
                    matched_count=len(matched),
                    total_amount=_money_text(total),
                    filters=[],
                    message=fallback_message,
                    kind="category_breakdown",
                    summary=AiFinanceQuestionSummary(matched_count=len(matched), total_amount=_money_text(total)),
                    cta=AiFinanceQuestionCta(label="Ver transacoes", route="/transactions", query={}) if matched else None,
                )

        return AiFinanceQuestionResponse(
            answer=message,
            matched_count=len(matched),
            total_amount=_money_text(total),
            filters=filters,
            message=message,
            kind="transactions_summary",
            summary=AiFinanceQuestionSummary(matched_count=len(matched), total_amount=_money_text(total), period_label=period_label),
            cta=cta,
        )

    def _month_transactions(self, transactions: list[dict[str, Any]], current_month: date | None) -> list[dict[str, Any]]:
        if not current_month:
            return transactions
        return [
            item
            for item in transactions
            if (parsed := _parse_date(item.get("transaction_date")))
            and parsed.year == current_month.year
            and parsed.month == current_month.month
        ]

    def _insights(
        self,
        transactions: list[dict[str, Any]],
        previous_transactions: list[dict[str, Any]],
        category_by_id: dict[str, dict[str, Any]],
        income_total: Decimal,
        expense_total: Decimal,
        net_total: Decimal,
    ) -> list[AiFinanceInsight]:
        insights = [
            AiFinanceInsight(
                title="Resultado do período",
                description=f"Seu resultado está em {_money_text(net_total)}.",
                severity="positive" if net_total >= 0 else "warning",
            )
        ]
        if income_total > 0:
            ratio = (expense_total / income_total) * Decimal("100")
            insights.append(
                AiFinanceInsight(
                    title="Relação gastos/entradas",
                    description=f"As saídas representam {ratio.quantize(Decimal('0.1'))}% das entradas.",
                    severity="warning" if ratio > 80 else "info",
                )
            )
        if previous_transactions:
            previous_income = sum((_money(item.get("amount")) for item in previous_transactions if item.get("type") in INCOME_TYPES), Decimal("0"))
            previous_expense = sum((_money(item.get("amount")) for item in previous_transactions if item.get("type") in EXPENSE_TYPES), Decimal("0"))
            previous_net = previous_income - previous_expense
            expense_delta = expense_total - previous_expense
            net_delta = net_total - previous_net
            expense_direction = "aumentaram" if expense_delta > 0 else "cairam" if expense_delta < 0 else "ficaram iguais"
            net_direction = "melhorou" if net_delta > 0 else "piorou" if net_delta < 0 else "ficou igual"
            insights.append(
                AiFinanceInsight(
                    title="Comparacao com periodo anterior",
                    description=(
                        f"As saidas {expense_direction} {_money_text(abs(expense_delta))} "
                        f"e o resultado {net_direction} {_money_text(abs(net_delta))}."
                    ),
                    severity="warning" if expense_delta > 0 and net_delta < 0 else "positive" if net_delta > 0 else "info",
                )
            )
        top_category = self._top_expense_categories(transactions, category_by_id, limit=1)
        if top_category:
            name, amount = top_category[0]
            insights.append(
                AiFinanceInsight(
                    title="Maior grupo de gastos",
                    description=f"{name} concentrou {_money_text(amount)} em saídas.",
                    severity="info",
                )
            )
        return insights

    def _payee_aliases(self, user_id: str) -> list[dict[str, Any]]:
        list_aliases = getattr(self.repository, "list_payee_aliases", None)
        if not list_aliases:
            return []
        return list_aliases(user_id)

    def _canonical_description(self, description: str, payee_aliases: list[dict[str, Any]]) -> str:
        normalized = _normalize_description(description)
        for alias in payee_aliases:
            normalized_alias = str(alias.get("normalized_alias") or "").strip()
            canonical_name = str(alias.get("canonical_name") or "").strip()
            if normalized_alias and canonical_name and normalized_alias in normalized:
                return canonical_name
        return description

    def _suggest_rules(
        self,
        transactions: list[dict[str, Any]],
        category_by_id: dict[str, dict[str, Any]],
        rules: list[dict[str, Any]],
    ) -> list[AiSuggestedRule]:
        existing_keywords = {_normalize_description(rule.get("keyword", "")) for rule in rules if rule.get("status") == "active"}
        grouped: dict[tuple[str, str, str], int] = defaultdict(int)
        for item in transactions:
            category_id = item.get("category_id")
            if not category_id or category_id not in category_by_id:
                continue
            keyword = _keyword(item.get("description", ""))
            if not keyword or keyword in existing_keywords:
                continue
            grouped[(keyword, category_id, str(item.get("type") or ""))] += 1
        suggestions = [
            AiSuggestedRule(
                keyword=keyword,
                category_id=category_id,
                category_name=category_by_id[category_id]["name"],
                transaction_type=transaction_type or None,
                match_count=count,
                conditions=[{"field": "combined_description", "operator": "contains", "value": keyword}],
                condition_logic="all",
                actions=[{"type": "set_category", "category_id": category_id}],
                rule_version=2,
                reason="Várias transações semelhantes já usam esta categoria.",
            )
            for (keyword, category_id, transaction_type), count in grouped.items()
            if count >= 2
        ]
        return sorted(suggestions, key=lambda item: item.match_count, reverse=True)[:5]

    def _suggest_payee_aliases(
        self,
        transactions: list[dict[str, Any]],
        payee_aliases: list[dict[str, Any]],
    ) -> list[AiSuggestedPayeeAlias]:
        existing_aliases = {_normalize_description(alias.get("alias", "")) for alias in payee_aliases}
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in transactions:
            description = str(item.get("original_description") or item.get("description") or "")
            fingerprint = _alias_fingerprint(description)
            if not fingerprint or fingerprint in existing_aliases:
                continue
            grouped[fingerprint].append(item)

        suggestions: list[AiSuggestedPayeeAlias] = []
        for fingerprint, items in grouped.items():
            raw_aliases: list[str] = []
            samples: list[str] = []
            for item in items:
                description = str(item.get("original_description") or item.get("description") or "")
                normalized_description = _normalize_description(description)
                if normalized_description and normalized_description not in {_normalize_description(alias) for alias in raw_aliases}:
                    raw_aliases.append(description[:80])
                if description and description not in samples:
                    samples.append(description[:120])
            if len({_normalize_description(alias) for alias in raw_aliases}) < 2:
                continue
            suggestions.append(
                AiSuggestedPayeeAlias(
                    canonical_name=_category_candidate_name(fingerprint),
                    aliases=raw_aliases[:4],
                    match_count=len(items),
                    sample_descriptions=samples[:3],
                    reason="Descricoes parecem representar o mesmo estabelecimento, mas precisam de confirmacao antes de mesclar.",
                )
            )
        return sorted(suggestions, key=lambda item: item.match_count, reverse=True)[:5]

    def _suggest_new_categories(
        self,
        transactions: list[dict[str, Any]],
        category_by_id: dict[str, dict[str, Any]],
    ) -> list[AiSuggestedCategory]:
        existing_names = {_normalize_description(category.get("name", "")) for category in category_by_id.values()}
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

        for item in transactions:
            keyword = _keyword(item.get("description", ""))
            if not keyword:
                continue

            category = category_by_id.get(item.get("category_id"))
            category_name = _normalize_description(category.get("name", "")) if category else ""
            if category and category_name not in GENERIC_CATEGORY_NAMES:
                continue

            candidate_name = _category_candidate_name(keyword.split()[0])
            candidate_key = _normalize_description(candidate_name)
            if not candidate_key or candidate_key in existing_names:
                continue

            grouped[(candidate_name, str(item.get("type") or "expense"))].append(item)

        suggestions: list[AiSuggestedCategory] = []
        for (name, transaction_type), items in grouped.items():
            if len(items) < 2:
                continue
            samples = []
            for item in items:
                description = item.get("description", "")
                if description and description not in samples:
                    samples.append(description)
                if len(samples) == 3:
                    break
            suggestions.append(
                AiSuggestedCategory(
                    name=name,
                    type="income" if transaction_type in INCOME_TYPES else "expense",
                    match_count=len(items),
                    sample_descriptions=samples,
                    reason="Transacoes recorrentes ficaram sem categoria especifica ou em uma categoria generica.",
                )
            )

        return sorted(suggestions, key=lambda item: item.match_count, reverse=True)[:5]

    def _suggest_categories(
        self,
        transactions: list[dict[str, Any]],
        category_by_id: dict[str, dict[str, Any]],
    ) -> list[AiCategorySuggestion]:
        learned: dict[str, Counter[str]] = defaultdict(Counter)
        for item in transactions:
            keyword = _keyword(item.get("description", ""))
            category_id = item.get("category_id")
            if keyword and category_id:
                learned[keyword][category_id] += 1

        suggestions: list[AiCategorySuggestion] = []
        for item in transactions:
            if item.get("category_id"):
                continue
            keyword = _keyword(item.get("description", ""))
            if not keyword or keyword not in learned:
                continue
            category_id, count = learned[keyword].most_common(1)[0]
            category = category_by_id.get(category_id)
            if not category:
                continue
            suggestions.append(
                AiCategorySuggestion(
                    transaction_id=item["id"],
                    description=item.get("description", ""),
                    suggested_category_id=category_id,
                    suggested_category_name=category["name"],
                    reason=f"{count} transações parecidas já usam essa categoria.",
                )
            )
        return suggestions[:8]

    def _suggest_recurrences(self, transactions: list[dict[str, Any]], payee_aliases: list[dict[str, Any]] | None = None) -> list[AiRecurrenceSuggestion]:
        grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in transactions:
            description = self._canonical_description(item.get("description", ""), payee_aliases or [])
            key = (_normalize_description(description), _money_text(_money(item.get("amount"))), str(item.get("type") or ""))
            if key[0]:
                grouped[key].append(item)
        suggestions: list[AiRecurrenceSuggestion] = []
        for (description, amount, transaction_type), items in grouped.items():
            months = {
                (parsed.year, parsed.month)
                for item in items
                if (parsed := _parse_date(item.get("transaction_date")))
            }
            if len(months) < 2:
                continue
            suggestions.append(
                AiRecurrenceSuggestion(
                    description=items[0].get("description", description),
                    amount=amount,
                    transaction_type=transaction_type,
                    occurrences=len(items),
                    cadence="mensal provável",
                    reason="O mesmo valor apareceu em meses diferentes.",
                )
            )
        return sorted(suggestions, key=lambda item: item.occurrences, reverse=True)[:6]

    def _suggest_renames(self, transactions: list[dict[str, Any]]) -> list[AiRenameSuggestion]:
        suggestions: list[AiRenameSuggestion] = []
        for item in transactions:
            current = item.get("description", "")
            suggested = _pretty_description(current)
            if suggested and suggested != current and len(suggested) >= 4:
                suggestions.append(
                    AiRenameSuggestion(
                        transaction_id=item["id"],
                        current_description=current,
                        suggested_description=suggested,
                        reason="Descrição parece conter ruído ou caixa alta.",
                    )
                )
        return suggestions[:8]

    def _top_expense_categories(
        self,
        transactions: list[dict[str, Any]],
        category_by_id: dict[str, dict[str, Any]],
        limit: int,
    ) -> list[tuple[str, Decimal]]:
        totals: dict[str, Decimal] = defaultdict(Decimal)
        for item in transactions:
            if item.get("type") not in EXPENSE_TYPES:
                continue
            category_id = item.get("category_id")
            name = category_by_id.get(category_id, {}).get("name", "Sem categoria")
            totals[name] += _money(item.get("amount"))
        return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]

    def _question_month(self, question: str) -> int | None:
        months = {
            "janeiro": 1,
            "fevereiro": 2,
            "marco": 3,
            "março": 3,
            "abril": 4,
            "maio": 5,
            "junho": 6,
            "julho": 7,
            "agosto": 8,
            "setembro": 9,
            "outubro": 10,
            "novembro": 11,
            "dezembro": 12,
        }
        for name, month in months.items():
            if name in question:
                return month
        return None

    def _question_period(self, question: str, transactions: list[dict[str, Any]]) -> tuple[date, date, str] | None:
        transaction_dates = [parsed for item in transactions if (parsed := _parse_date(item.get("transaction_date")))]
        reference = max(transaction_dates, default=date.today())
        if any(term in question for term in ["esse mes", "este mes", "mes atual"]):
            start = date(reference.year, reference.month, 1)
            next_month = date(reference.year + int(reference.month == 12), 1 if reference.month == 12 else reference.month + 1, 1)
            return start, date.fromordinal(next_month.toordinal() - 1), "neste mes"

        month_number = self._question_month(question)
        if month_number:
            start = date(reference.year, month_number, 1)
            next_month = date(reference.year + int(month_number == 12), 1 if month_number == 12 else month_number + 1, 1)
            return start, date.fromordinal(next_month.toordinal() - 1), f"em {month_number:02d}/{reference.year}"
        return None

    def _question_keyword(self, question: str) -> str | None:
        ignored = {
            "quanto",
            "gastei",
            "gasto",
            "gastos",
            "despesa",
            "despesas",
            "receita",
            "receitas",
            "esse",
            "este",
            "mes",
            "com",
            "em",
            "de",
            "no",
            "na",
        }
        words = [word for word in question.split() if len(word) >= 3 and word not in ignored]
        return " ".join(words[:2]) if words else None

    def _answer_message(self, matched_count: int, total: Decimal, period_label: str | None) -> str:
        transaction_label = "transacao" if matched_count == 1 else "transacoes"
        period_text = f" {period_label}" if period_label else ""
        return f"Encontrei {matched_count} {transaction_label}{period_text}, no valor total de {_brl_text(total)}."
