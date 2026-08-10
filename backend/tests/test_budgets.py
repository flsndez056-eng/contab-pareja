from decimal import Decimal

from app.services.budgets import amount_status


def test_budget_money_is_serialized_with_stable_precision() -> None:
    status = amount_status(Decimal("1000"), Decimal("0"))

    assert status.limit == Decimal("1000.00")
    assert status.spent == Decimal("0.00")
    assert status.remaining == Decimal("1000.00")
