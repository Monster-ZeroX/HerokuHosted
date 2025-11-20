"""Billing service using Genie Business Connect."""
from __future__ import annotations

from typing import Tuple

from webapp.models import db, Transaction, User


class BillingService:
    def __init__(self):
        pass

    def record_transaction(self, user: User, amount: float, currency: str = "USD", status: str = "pending", provider_id: str | None = None) -> Transaction:
        txn = Transaction(user_id=user.id, amount=amount, currency=currency, status=status, provider_transaction_id=provider_id)
        db.session.add(txn)
        db.session.commit()
        return txn

    def list_transactions(self, page: int, page_size: int):
        query = Transaction.query.order_by(Transaction.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total
