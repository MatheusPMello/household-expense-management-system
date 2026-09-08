import uuid
from datetime import date
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.household import Household, HouseholdMember
from app.models.person import Person
from app.models.fixed_template import FixedExpenseTemplate
from app.models.cycle import BillingCycle
from app.models.expense import Expense, ExpenseSplit
from app.models.payment import Payment
from app.models.debt_waiver import DebtWaiver
from app.services.split_engine import calculate_splits, SplitEngineError
from app.services.cycle_service import (
    create_billing_cycle,
    verify_cycle_is_open,
    get_safe_due_date,
)
from app.services.balance_service import (
    calculate_cycle_report,
    calculate_general_balance_report,
)
from fastapi import HTTPException


def test_split_engine_edge_cases():
    p1, p2 = uuid.uuid4(), uuid.uuid4()

    # Zero or negative amount
    with pytest.raises(SplitEngineError, match="greater than 0"):
        calculate_splits(total_amount_cents=0, split_type="EQUAL", participant_ids=[p1])

    with pytest.raises(SplitEngineError, match="greater than 0"):
        calculate_splits(total_amount_cents=-100, split_type="EQUAL", participant_ids=[p1])

    # Unsupported split type
    with pytest.raises(SplitEngineError, match="Unsupported split type"):
        calculate_splits(total_amount_cents=100, split_type="MAGIC", participant_ids=[p1])

    # EQUAL with empty participants
    with pytest.raises(SplitEngineError, match="at least one participant"):
        calculate_splits(total_amount_cents=100, split_type="EQUAL", participant_ids=[])

    # PERCENTAGE with empty percentages
    with pytest.raises(SplitEngineError, match="requires participant percentages"):
        calculate_splits(total_amount_cents=100, split_type="PERCENTAGE", percentages={})

    # PERCENTAGE with negative percentage
    with pytest.raises(SplitEngineError, match="Percentages cannot be negative"):
        calculate_splits(
            total_amount_cents=100,
            split_type="PERCENTAGE",
            percentages={p1: -10.0, p2: 110.0},
        )

    # EXACT with negative amount
    with pytest.raises(SplitEngineError, match="cannot be negative"):
        calculate_splits(
            total_amount_cents=100,
            split_type="EXACT",
            exact_amounts={p1: -50, p2: 150},
        )

    # EXACT with empty exact_amounts
    with pytest.raises(SplitEngineError, match="requires specified amounts"):
        calculate_splits(total_amount_cents=100, split_type="EXACT", exact_amounts={})

    # WEIGHTED with empty weights
    with pytest.raises(SplitEngineError, match="requires participant weights"):
        calculate_splits(total_amount_cents=100, split_type="WEIGHTED", weights={})

    # WEIGHTED with zero total weight
    with pytest.raises(SplitEngineError, match="greater than zero"):
        calculate_splits(
            total_amount_cents=100,
            split_type="WEIGHTED",
            weights={p1: 0, p2: 0},
        )

    # WEIGHTED with negative weight
    with pytest.raises(SplitEngineError, match="greater than zero"):
        calculate_splits(
            total_amount_cents=100,
            split_type="WEIGHTED",
            weights={p1: -1, p2: 3},
        )


def test_safe_due_date():
    # Leap year vs non-leap year
    assert get_safe_due_date(2024, 2, 31) == date(2024, 2, 29)
    assert get_safe_due_date(2023, 2, 31) == date(2023, 2, 28)
    assert get_safe_due_date(2026, 4, 31) == date(2026, 4, 30)
    assert get_safe_due_date(2026, 9, 15) == date(2026, 9, 15)


def test_verify_cycle_is_open():
    open_cycle = BillingCycle(year=2026, month=9, status="OPEN")
    verify_cycle_is_open(open_cycle)  # Should not raise

    closed_cycle = BillingCycle(year=2026, month=9, status="CLOSED")
    with pytest.raises(HTTPException) as exc_info:
        verify_cycle_is_open(closed_cycle)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_balance_service_direct_calculation(db_session: AsyncSession):
    # Setup Household
    hh = Household(name="Direct Test Home")
    db_session.add(hh)
    await db_session.flush()

    p1 = Person(household_id=hh.id, name="Person 1", is_active=True)
    p2 = Person(household_id=hh.id, name="Person 2", is_active=True)
    p3_inactive = Person(household_id=hh.id, name="Inactive Person", is_active=False)
    db_session.add_all([p1, p2, p3_inactive])
    await db_session.flush()

    # Create cycle
    cycle = BillingCycle(household_id=hh.id, year=2026, month=10, status="OPEN")
    db_session.add(cycle)
    await db_session.flush()

    # Add expense
    exp = Expense(
        billing_cycle_id=cycle.id,
        title="Internet",
        total_amount_cents=10000,
        is_fixed=True,
        category="Utilities",
        due_date=date(2026, 10, 15),
        paid_to_vendor=True,
        split_type="EQUAL",
    )
    db_session.add(exp)
    await db_session.flush()

    s1 = ExpenseSplit(expense_id=exp.id, person_id=p1.id, assigned_amount_cents=5000)
    s2 = ExpenseSplit(expense_id=exp.id, person_id=p2.id, assigned_amount_cents=5000)
    db_session.add_all([s1, s2])

    # Payment for p1: 6000 cents (overpayment credit)
    pay1 = Payment(
        billing_cycle_id=cycle.id, person_id=p1.id, amount_cents=6000
    )
    # Payment for p2: 3000 cents
    pay2 = Payment(
        billing_cycle_id=cycle.id, person_id=p2.id, amount_cents=3000
    )
    # Waiver for p2: 2000 cents
    w2 = DebtWaiver(
        billing_cycle_id=cycle.id,
        person_id=p2.id,
        amount_cents=2000,
        reason="Direct test waiver",
    )
    db_session.add_all([pay1, pay2, w2])
    await db_session.commit()

    # Calculate cycle report
    report = await calculate_cycle_report(db_session, cycle.id)
    assert report.total_budget_cents == 10000
    assert report.total_paid_to_vendor_cents == 10000
    assert report.total_collected_cents == 9000
    assert report.total_waived_cents == 2000

    r_map = {r.person_id: r for r in report.residents}
    # p1: assigned 5000, paid 6000, remaining -1000 -> CREDIT
    assert r_map[p1.id].remaining_balance_cents == -1000
    assert r_map[p1.id].status == "CREDIT"

    # p2: assigned 5000, paid 3000, waived 2000, remaining 0 -> SETTLED
    assert r_map[p2.id].remaining_balance_cents == 0
    assert r_map[p2.id].status == "SETTLED"

    # Verify that cycle report omits inactive resident with zero transactions
    assert len(report.residents) == 2

    # Calculate general balance report (retains all historical persons)
    gen_report = await calculate_general_balance_report(db_session, hh.id)
    assert len(gen_report.residents) == 3
    assert len(gen_report.debt_waiver_ledger) == 1
    assert gen_report.debt_waiver_ledger[0].amount_cents == 2000
    assert len(gen_report.trajectory) == 1
    assert gen_report.trajectory[0].fixed_cents == 10000
    assert gen_report.trajectory[0].variable_cents == 0


@pytest.mark.asyncio
async def test_create_billing_cycle_direct(db_session: AsyncSession):
    hh = Household(name="Cycle Test Home")
    db_session.add(hh)
    await db_session.flush()

    p1 = Person(household_id=hh.id, name="Alice", is_active=True)
    p2 = Person(household_id=hh.id, name="Bob", is_active=True)
    db_session.add_all([p1, p2])
    await db_session.flush()

    # Fixed template
    tpl = FixedExpenseTemplate(
        household_id=hh.id,
        title="Water Utility",
        estimated_amount_cents=8000,
        due_day=10,
        category="Utilities",
        is_active=True,
    )
    db_session.add(tpl)
    await db_session.commit()

    # Create cycle
    cycle = await create_billing_cycle(db_session, hh.id, 2026, 11)
    assert cycle.year == 2026
    assert cycle.month == 11
    assert cycle.status == "OPEN"

    # Duplicate cycle raises 409
    with pytest.raises(HTTPException) as exc:
        await create_billing_cycle(db_session, hh.id, 2026, 11)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_calculate_cycle_report_not_found(db_session: AsyncSession):
    with pytest.raises(ValueError, match="Billing cycle not found"):
        await calculate_cycle_report(db_session, uuid.uuid4())
