import uuid
import pytest
from app.services.split_engine import calculate_splits, SplitEngineError


def test_split_equal_perfect_cents():
    p1, p2, p3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    # 1000 cents divided by 3: 334, 333, 333
    splits = calculate_splits(
        total_amount_cents=1000,
        split_type="EQUAL",
        participant_ids=[p1, p2, p3],
    )
    assert len(splits) == 3
    assert sum(s.assigned_amount_cents for s in splits) == 1000
    assert splits[0].assigned_amount_cents == 334
    assert splits[1].assigned_amount_cents == 333
    assert splits[2].assigned_amount_cents == 333


def test_split_equal_single_person():
    p1 = uuid.uuid4()
    splits = calculate_splits(
        total_amount_cents=1575,
        split_type="EQUAL",
        participant_ids=[p1],
    )
    assert len(splits) == 1
    assert splits[0].assigned_amount_cents == 1575


def test_split_percentage_with_rounding_residual():
    p1, p2, p3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    # 1000 cents: 50%, 25%, 25% -> 500, 250, 250
    splits = calculate_splits(
        total_amount_cents=1000,
        split_type="PERCENTAGE",
        percentages={p1: 50.0, p2: 25.0, p3: 25.0},
    )
    assert sum(s.assigned_amount_cents for s in splits) == 1000

    # Test odd total with percentage rounding: 10001 cents with 33.33%, 33.33%, 33.34%
    splits_odd = calculate_splits(
        total_amount_cents=10001,
        split_type="PERCENTAGE",
        percentages={p1: 33.34, p2: 33.33, p3: 33.33},
    )
    assert sum(s.assigned_amount_cents for s in splits_odd) == 10001


def test_split_percentage_invalid_sum():
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    with pytest.raises(SplitEngineError, match="Percentages must sum to 100.0%"):
        calculate_splits(
            total_amount_cents=1000,
            split_type="PERCENTAGE",
            percentages={p1: 50.0, p2: 40.0},
        )


def test_split_exact_success_and_failure():
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    # Valid exact
    splits = calculate_splits(
        total_amount_cents=5000,
        split_type="EXACT",
        exact_amounts={p1: 3000, p2: 2000},
    )
    assert sum(s.assigned_amount_cents for s in splits) == 5000

    # Invalid exact mismatch
    with pytest.raises(SplitEngineError, match="Sum of exact splits"):
        calculate_splits(
            total_amount_cents=5000,
            split_type="EXACT",
            exact_amounts={p1: 3000, p2: 1500},
        )


def test_split_weighted():
    p1, p2 = uuid.uuid4(), uuid.uuid4()
    # 100 cents, weights 2 and 1 -> 67 and 33
    splits = calculate_splits(
        total_amount_cents=100,
        split_type="WEIGHTED",
        weights={p1: 2.0, p2: 1.0},
    )
    assert sum(s.assigned_amount_cents for s in splits) == 100
    p1_alloc = next(s for s in splits if s.person_id == p1).assigned_amount_cents
    p2_alloc = next(s for s in splits if s.person_id == p2).assigned_amount_cents
    assert p1_alloc == 67
    assert p2_alloc == 33
