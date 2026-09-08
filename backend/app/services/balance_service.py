import uuid
from typing import Dict, List, Tuple
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cycle import BillingCycle
from app.models.person import Person
from app.models.expense import Expense, ExpenseSplit
from app.models.payment import Payment
from app.models.debt_waiver import DebtWaiver
from app.schemas.report import (
    ResidentCycleBalance,
    CurrentCycleReport,
    ResidentHistoricalSummary,
    DebtWaiverLedgerEntry,
    MonthlyTrajectoryPoint,
    GeneralBalanceReport,
)
from app.schemas.expense import ExpenseOut, ExpenseSplitOut


def _compute_resident_balances(
    persons: List[Person],
    expenses: List[Expense],
    payments: List[Payment],
    waivers: List[DebtWaiver],
) -> List[ResidentCycleBalance]:
    person_assigned: Dict[uuid.UUID, int] = {p.id: 0 for p in persons}
    person_paid: Dict[uuid.UUID, int] = {p.id: 0 for p in persons}
    person_waived: Dict[uuid.UUID, int] = {p.id: 0 for p in persons}

    for exp in expenses:
        for split in exp.splits:
            if split.person_id in person_assigned:
                person_assigned[split.person_id] += split.assigned_amount_cents

    for pay in payments:
        if pay.person_id in person_paid:
            person_paid[pay.person_id] += pay.amount_cents

    for w in waivers:
        if w.person_id in person_waived:
            person_waived[w.person_id] += w.amount_cents

    residents: List[ResidentCycleBalance] = []
    for p in persons:
        assigned = person_assigned.get(p.id, 0)
        paid = person_paid.get(p.id, 0)
        waived = person_waived.get(p.id, 0)
        if not p.is_active and assigned == 0 and paid == 0 and waived == 0:
            continue

        remaining = assigned - (paid + waived)
        if remaining == 0:
            bal_status = "SETTLED"
        elif remaining > 0:
            bal_status = "OWES"
        else:
            bal_status = "CREDIT"

        residents.append(
            ResidentCycleBalance(
                person_id=p.id,
                person_name=p.name,
                assigned_cents=assigned,
                paid_cents=paid,
                waived_cents=waived,
                remaining_balance_cents=remaining,
                status=bal_status,
            )
        )
    return residents


def _format_cycle_expenses(
    expenses: List[Expense], person_map: Dict[uuid.UUID, Person]
) -> List[ExpenseOut]:
    expense_outs: List[ExpenseOut] = []
    for e in expenses:
        splits_out = [
            ExpenseSplitOut(
                id=s.id,
                expense_id=s.expense_id,
                person_id=s.person_id,
                person_name=person_map[s.person_id].name if s.person_id in person_map else "Unknown",
                assigned_amount_cents=s.assigned_amount_cents,
            )
            for s in e.splits
        ]
        expense_outs.append(
            ExpenseOut(
                id=e.id,
                billing_cycle_id=e.billing_cycle_id,
                template_id=e.template_id,
                title=e.title,
                total_amount_cents=e.total_amount_cents,
                is_fixed=e.is_fixed,
                category=e.category,
                due_date=e.due_date,
                is_paid=e.is_paid,
                split_type=e.split_type,
                status=e.status,
                created_at=e.created_at,
                splits=splits_out,
            )
        )
    return expense_outs


async def calculate_cycle_report(
    db: AsyncSession, cycle_id: uuid.UUID
) -> CurrentCycleReport:
    # 1. Load cycle with household
    cycle_stmt = select(BillingCycle).where(BillingCycle.id == cycle_id)
    cycle = (await db.execute(cycle_stmt)).scalar_one_or_none()
    if not cycle:
        raise ValueError("Billing cycle not found.")

    # 2. Load all persons in household (both active and inactive who might have splits)
    persons_stmt = select(Person).where(Person.household_id == cycle.household_id)
    persons = (await db.execute(persons_stmt)).scalars().all()
    person_map: Dict[uuid.UUID, Person] = {p.id: p for p in persons}

    # 3. Load expenses with splits for this cycle
    exp_stmt = (
        select(Expense)
        .where(Expense.billing_cycle_id == cycle_id)
        .options(selectinload(Expense.splits))
        .order_by(Expense.due_date, Expense.created_at)
    )
    expenses = (await db.execute(exp_stmt)).scalars().all()

    # 4. Load payments for this cycle
    pay_stmt = select(Payment).where(Payment.billing_cycle_id == cycle_id)
    payments = (await db.execute(pay_stmt)).scalars().all()

    # 5. Load waivers for this cycle
    waiver_stmt = select(DebtWaiver).where(DebtWaiver.billing_cycle_id == cycle_id)
    waivers = (await db.execute(waiver_stmt)).scalars().all()

    # Aggregations
    total_budget_cents = sum(e.total_amount_cents for e in expenses)
    total_paid_cents = sum(e.total_amount_cents for e in expenses if e.is_paid)
    total_collected_cents = sum(p.amount_cents for p in payments)
    total_waived_cents = sum(w.amount_cents for w in waivers)

    # Sub-breakdowns
    residents = _compute_resident_balances(persons, expenses, payments, waivers)
    expense_outs = _format_cycle_expenses(expenses, person_map)

    return CurrentCycleReport(
        cycle_id=cycle.id,
        year=cycle.year,
        month=cycle.month,
        status=cycle.status,
        total_budget_cents=total_budget_cents,
        total_paid_cents=total_paid_cents,
        total_collected_cents=total_collected_cents,
        total_waived_cents=total_waived_cents,
        residents=residents,
        expenses=expense_outs,
    )


def _aggregate_expenses_and_trajectory(
    cycles: List[BillingCycle],
    expenses: List[Expense],
    hist_assigned: Dict[uuid.UUID, int],
) -> List[MonthlyTrajectoryPoint]:
    cycle_fixed: Dict[uuid.UUID, int] = {c.id: 0 for c in cycles}
    cycle_var: Dict[uuid.UUID, int] = {c.id: 0 for c in cycles}

    for exp in expenses:
        if exp.is_fixed:
            cycle_fixed[exp.billing_cycle_id] += exp.total_amount_cents
        else:
            cycle_var[exp.billing_cycle_id] += exp.total_amount_cents

        for split in exp.splits:
            if split.person_id in hist_assigned:
                hist_assigned[split.person_id] += split.assigned_amount_cents

    trajectory: List[MonthlyTrajectoryPoint] = []
    for c in cycles:
        f_cents = cycle_fixed[c.id]
        v_cents = cycle_var[c.id]
        trajectory.append(
            MonthlyTrajectoryPoint(
                cycle_id=c.id,
                year=c.year,
                month=c.month,
                fixed_cents=f_cents,
                variable_cents=v_cents,
                total_cents=f_cents + v_cents,
            )
        )
    return trajectory


def _build_waiver_ledger(
    waivers: List[DebtWaiver],
    cycle_map: Dict[uuid.UUID, BillingCycle],
    person_map: Dict[uuid.UUID, Person],
    hist_waived: Dict[uuid.UUID, int],
) -> List[DebtWaiverLedgerEntry]:
    debt_waiver_ledger: List[DebtWaiverLedgerEntry] = []
    for w in waivers:
        if w.person_id in hist_waived:
            hist_waived[w.person_id] += w.amount_cents

        c = cycle_map.get(w.billing_cycle_id)
        c_year = c.year if c else 0
        c_month = c.month if c else 0
        p_name = person_map[w.person_id].name if w.person_id in person_map else "Unknown"

        debt_waiver_ledger.append(
            DebtWaiverLedgerEntry(
                id=w.id,
                billing_cycle_id=w.billing_cycle_id,
                cycle_year=c_year,
                cycle_month=c_month,
                person_id=w.person_id,
                person_name=p_name,
                amount_cents=w.amount_cents,
                waived_at=w.waived_at,
                reason=w.reason,
            )
        )
    return debt_waiver_ledger


def _build_historical_summaries(
    persons: List[Person],
    hist_assigned: Dict[uuid.UUID, int],
    hist_paid: Dict[uuid.UUID, int],
    hist_waived: Dict[uuid.UUID, int],
) -> List[ResidentHistoricalSummary]:
    residents_summary: List[ResidentHistoricalSummary] = []
    for p in persons:
        assigned = hist_assigned.get(p.id, 0)
        paid = hist_paid.get(p.id, 0)
        waived = hist_waived.get(p.id, 0)
        outstanding = assigned - (paid + waived)
        compliance = round((paid / assigned) * 100.0, 2) if assigned > 0 else 100.0

        residents_summary.append(
            ResidentHistoricalSummary(
                person_id=p.id,
                person_name=p.name,
                total_assigned_cents=assigned,
                total_paid_cents=paid,
                total_waived_cents=waived,
                compliance_rate_percent=compliance,
                outstanding_historical_balance_cents=outstanding,
            )
        )
    return residents_summary


async def calculate_general_balance_report(
    db: AsyncSession, household_id: uuid.UUID
) -> GeneralBalanceReport:
    # 1. Fetch persons
    p_stmt = select(Person).where(Person.household_id == household_id)
    persons = (await db.execute(p_stmt)).scalars().all()
    person_map = {p.id: p for p in persons}

    # 2. Fetch cycles for this household
    c_stmt = (
        select(BillingCycle)
        .where(BillingCycle.household_id == household_id)
        .order_by(BillingCycle.year, BillingCycle.month)
    )
    cycles = (await db.execute(c_stmt)).scalars().all()
    cycle_ids = [c.id for c in cycles]

    # Initialize resident historical stats
    hist_assigned: Dict[uuid.UUID, int] = {p.id: 0 for p in persons}
    hist_paid: Dict[uuid.UUID, int] = {p.id: 0 for p in persons}
    hist_waived: Dict[uuid.UUID, int] = {p.id: 0 for p in persons}

    trajectory: List[MonthlyTrajectoryPoint] = []
    debt_waiver_ledger: List[DebtWaiverLedgerEntry] = []
    cycle_map = {c.id: c for c in cycles}

    if cycle_ids:
        # Fetch all expenses in all cycles
        exp_stmt = (
            select(Expense)
            .where(Expense.billing_cycle_id.in_(cycle_ids))
            .options(selectinload(Expense.splits))
        )
        expenses = (await db.execute(exp_stmt)).scalars().all()
        trajectory = _aggregate_expenses_and_trajectory(cycles, expenses, hist_assigned)

        # Fetch all payments
        pay_stmt = select(Payment).where(Payment.billing_cycle_id.in_(cycle_ids))
        payments = (await db.execute(pay_stmt)).scalars().all()
        for p in payments:
            if p.person_id in hist_paid:
                hist_paid[p.person_id] += p.amount_cents

        # Fetch all debt waivers
        waiver_stmt = (
            select(DebtWaiver)
            .where(DebtWaiver.billing_cycle_id.in_(cycle_ids))
            .order_by(DebtWaiver.waived_at.desc())
        )
        waivers = (await db.execute(waiver_stmt)).scalars().all()
        debt_waiver_ledger = _build_waiver_ledger(waivers, cycle_map, person_map, hist_waived)

    residents_summary = _build_historical_summaries(
        persons, hist_assigned, hist_paid, hist_waived
    )

    return GeneralBalanceReport(
        household_id=household_id,
        residents=residents_summary,
        debt_waiver_ledger=debt_waiver_ledger,
        trajectory=trajectory,
    )
