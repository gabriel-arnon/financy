from enum import StrEnum


class TransactionType(StrEnum):
    expense = "expense"
    income = "income"
    transfer = "transfer"
    payment = "payment"
    refund = "refund"


class TransactionStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    reconciled = "reconciled"
    ignored = "ignored"


class PreviewStatus(StrEnum):
    pending = "pending"
    selected = "selected"
    ignored = "ignored"
    confirmed = "confirmed"
    duplicate = "duplicate"
    error = "error"


class ExcludedReason(StrEnum):
    subtotal = "subtotal"
    total = "total"
    saldo_anterior = "saldo_anterior"
    informativo = "informativo"
    duplicate = "duplicate"
    payment = "payment"
    refund = "refund"
    low_confidence = "low_confidence"


class AccountType(StrEnum):
    checking = "checking"
    savings = "savings"
    wallet = "wallet"
    investment = "investment"


class EntityStatus(StrEnum):
    active = "active"
    inactive = "inactive"


class CategoryType(StrEnum):
    expense = "expense"
    income = "income"
    both = "both"


class ClassificationMatchScope(StrEnum):
    description = "description"
    original_description = "original_description"
    both = "both"
