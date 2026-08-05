from app.models.entities import (
    CoupleMember,
    EmailActionToken,
    Expense,
    ExpenseDecision,
    IdempotencyRecord,
)


def constraint_names(model: type) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints if constraint.name}


def test_database_enforces_two_member_slots() -> None:
    names = constraint_names(CoupleMember)
    assert "ck_couple_members_valid_slot" in names
    assert "uq_couple_members_couple_slot" in names


def test_approval_cannot_create_duplicate_ledger_entry() -> None:
    assert "uq_expenses_request_id" in constraint_names(Expense)
    assert "uq_expense_decisions_request_id" in constraint_names(ExpenseDecision)


def test_idempotency_key_is_unique_per_user_and_scope() -> None:
    assert "uq_idempotency_user_scope_key" in constraint_names(IdempotencyRecord)


def test_email_action_token_is_unique_and_has_a_valid_purpose() -> None:
    names = constraint_names(EmailActionToken)
    assert "uq_email_action_tokens_token_hash" in names
    assert "ck_email_action_tokens_valid_purpose" in names
