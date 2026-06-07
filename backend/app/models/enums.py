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
