"""Synthetic demo data. No real people or accounts.

Used by the Plaid mock and by the stub endpoints in app/api/finance.py.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid5

from app.integrations.plaid.base import PlaidAccount, PlaidTransaction
from app.schemas.finance import Account, ConnectionStatus, Transaction, TransactionState

_NS = UUID("6f1c1f9e-6a43-4c7e-9a52-2d7a0b6a9f10")
AS_OF = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def demo_id(name: str) -> UUID:
    return uuid5(_NS, name)


PLAID_ACCOUNTS = [
    PlaidAccount(
        account_id="acc-checking",
        name="Student Checking",
        type="depository",
        subtype="checking",
        current_balance=Decimal("842.17"),
        available_balance=Decimal("812.17"),
        currency="USD",
    ),
    PlaidAccount(
        account_id="acc-savings",
        name="Emergency Savings",
        type="depository",
        subtype="savings",
        current_balance=Decimal("350.00"),
        available_balance=Decimal("350.00"),
        currency="USD",
    ),
    PlaidAccount(
        account_id="acc-credit",
        name="Starter Credit Card",
        type="credit",
        subtype="credit card",
        current_balance=Decimal("124.60"),
        available_balance=Decimal("375.40"),
        currency="USD",
    ),
]

# (id, account, amount, date, name, merchant, category, pending)
_TXNS = [
    ("txn-01", "acc-checking", "-1250.00", "2026-10-01", "PELL GRANT DISB", None, "INCOME", False),
    ("txn-02", "acc-checking", "450.00", "2026-10-02", "Rent", None, "RENT_AND_UTILITIES", False),
    (
        "txn-03",
        "acc-checking",
        "-310.25",
        "2026-10-15",
        "Work-Study Payroll",
        None,
        "INCOME",
        False,
    ),
    (
        "txn-04",
        "acc-credit",
        "42.18",
        "2026-10-16",
        "Campus Grocery",
        "Campus Grocery",
        "FOOD_AND_DRINK",
        False,
    ),
    (
        "txn-05",
        "acc-checking",
        "35.00",
        "2026-10-18",
        "Phone Plan",
        "Mobile Co",
        "RENT_AND_UTILITIES",
        False,
    ),
    (
        "txn-06",
        "acc-credit",
        "12.99",
        "2026-10-20",
        "Streaming",
        "StreamCo",
        "ENTERTAINMENT",
        False,
    ),
    (
        "txn-07",
        "acc-checking",
        "60.00",
        "2026-10-22",
        "Transfer to savings",
        None,
        "TRANSFER_OUT",
        False,
    ),
    (
        "txn-08",
        "acc-savings",
        "-60.00",
        "2026-10-22",
        "Transfer from checking",
        None,
        "TRANSFER_IN",
        False,
    ),
    (
        "txn-09",
        "acc-credit",
        "69.43",
        "2026-10-28",
        "Bookstore",
        "Campus Books",
        "GENERAL_MERCHANDISE",
        False,
    ),
    (
        "txn-10",
        "acc-checking",
        "18.50",
        "2026-10-31",
        "Coffee Shop",
        "Bean There",
        "FOOD_AND_DRINK",
        True,
    ),
]

PLAID_TRANSACTIONS = [
    PlaidTransaction(
        transaction_id=tid,
        account_id=acc,
        amount=Decimal(amount),
        currency="USD",
        date=date.fromisoformat(day),
        authorized_date=None,
        name=name,
        merchant_name=merchant,
        category=category,
        pending=pending,
        pending_transaction_id=None,
    )
    for tid, acc, amount, day, name, merchant, category, pending in _TXNS
]


def accounts() -> list[Account]:
    return [
        Account(
            id=demo_id(a.account_id),
            name=a.name,
            type=a.type,
            subtype=a.subtype,
            current_balance=a.current_balance,
            available_balance=a.available_balance,
            currency=a.currency or "USD",
            connection_status=ConnectionStatus.healthy,
            last_synced_at=AS_OF,
        )
        for a in PLAID_ACCOUNTS
    ]


def transactions() -> list[Transaction]:
    return [
        Transaction(
            id=demo_id(t.transaction_id),
            account_id=demo_id(t.account_id),
            amount=t.amount,
            currency=t.currency or "USD",
            date=t.date,
            merchant_name=t.merchant_name or t.name,
            category=t.category,
            state=TransactionState.pending if t.pending else TransactionState.posted,
        )
        for t in sorted(PLAID_TRANSACTIONS, key=lambda t: t.date, reverse=True)
    ]
