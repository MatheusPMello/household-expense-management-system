import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SplitAssignment(BaseModel):
    person_id: uuid.UUID
    assigned_amount_cents: int = Field(ge=0)


class SplitEngineError(Exception):
    """Custom exception raised when split calculation fails validation."""
    pass


def _calculate_equal_splits(
    total_amount_cents: int, participant_ids: Optional[List[uuid.UUID]]
) -> List[SplitAssignment]:
    if not participant_ids:
        raise SplitEngineError("Equal split requires at least one participant.")

    # Deduplicate while preserving order
    unique_ids = list(dict.fromkeys(participant_ids))
    n = len(unique_ids)
    if n == 0:
        raise SplitEngineError("Equal split requires at least one participant.")

    quotient = total_amount_cents // n
    remainder = total_amount_cents % n

    results: List[SplitAssignment] = []
    for i, pid in enumerate(unique_ids):
        assigned = quotient + (1 if i < remainder else 0)
        results.append(SplitAssignment(person_id=pid, assigned_amount_cents=assigned))

    return results


def _calculate_percentage_splits(
    total_amount_cents: int, percentages: Optional[Dict[uuid.UUID, float]]
) -> List[SplitAssignment]:
    if not percentages:
        raise SplitEngineError("Percentage split requires participant percentages.")

    total_pct = sum(percentages.values())
    if abs(total_pct - 100.0) > 0.01:
        raise SplitEngineError(
            f"Percentages must sum to 100.0%. Current sum: {total_pct:.2f}%"
        )

    # Calculate base floor allocation and track fractional remainders
    allocations: Dict[uuid.UUID, int] = {}
    fractional_remainders: List[tuple[float, float, uuid.UUID]] = []
    base_sum = 0

    for pid, pct in percentages.items():
        if pct < 0:
            raise SplitEngineError("Percentages cannot be negative.")
        exact_val = total_amount_cents * (pct / 100.0)
        floor_val = int(exact_val)
        fraction = exact_val - floor_val
        allocations[pid] = floor_val
        base_sum += floor_val
        fractional_remainders.append((pct, fraction, pid))

    leftover_cents = total_amount_cents - base_sum
    fractional_remainders.sort(key=lambda item: (item[0], item[1], str(item[2])), reverse=True)

    for i in range(leftover_cents):
        pid = fractional_remainders[i % len(fractional_remainders)][2]
        allocations[pid] += 1

    return [
        SplitAssignment(person_id=pid, assigned_amount_cents=amount)
        for pid, amount in allocations.items()
    ]


def _calculate_exact_splits(
    total_amount_cents: int, exact_amounts: Optional[Dict[uuid.UUID, int]]
) -> List[SplitAssignment]:
    if not exact_amounts:
        raise SplitEngineError("Exact split requires specified amounts for participants.")

    for pid, amt in exact_amounts.items():
        if amt < 0:
            raise SplitEngineError(
                f"Assigned amount for participant {pid} cannot be negative."
            )

    exact_sum = sum(exact_amounts.values())
    if exact_sum != total_amount_cents:
        raise SplitEngineError(
            f"Sum of exact splits ({exact_sum} cents) does not match "
            f"total expense amount ({total_amount_cents} cents)."
        )

    return [
        SplitAssignment(person_id=pid, assigned_amount_cents=amt)
        for pid, amt in exact_amounts.items()
    ]


def _calculate_weighted_splits(
    total_amount_cents: int, weights: Optional[Dict[uuid.UUID, float]]
) -> List[SplitAssignment]:
    if not weights:
        raise SplitEngineError("Weighted split requires participant weights.")

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise SplitEngineError("Total weight must be greater than zero.")

    allocations = {}
    weighted_fractions: List[tuple[float, float, uuid.UUID]] = []
    base_sum = 0

    for pid, w in weights.items():
        if w <= 0:
            raise SplitEngineError("Weights must be greater than zero.")
        exact_val = total_amount_cents * (w / total_weight)
        floor_val = int(exact_val)
        fraction = exact_val - floor_val
        allocations[pid] = floor_val
        base_sum += floor_val
        weighted_fractions.append((w, fraction, pid))

    leftover_cents = total_amount_cents - base_sum
    weighted_fractions.sort(key=lambda item: (item[0], item[1], str(item[2])), reverse=True)

    for i in range(leftover_cents):
        pid = weighted_fractions[i % len(weighted_fractions)][2]
        allocations[pid] += 1

    return [
        SplitAssignment(person_id=pid, assigned_amount_cents=amount)
        for pid, amount in allocations.items()
    ]


def calculate_splits(
    total_amount_cents: int,
    split_type: str,
    participant_ids: Optional[List[uuid.UUID]] = None,
    percentages: Optional[Dict[uuid.UUID, float]] = None,
    exact_amounts: Optional[Dict[uuid.UUID, int]] = None,
    weights: Optional[Dict[uuid.UUID, float]] = None,
) -> List[SplitAssignment]:
    """
    Executes penny-perfect split calculation preserving integer precision cents.
    Guarantees sum(assigned_amount_cents) == total_amount_cents.
    """
    if total_amount_cents <= 0:
        raise SplitEngineError("Total amount must be greater than 0 cents.")

    split_type_upper = split_type.upper()

    if split_type_upper == "EQUAL":
        return _calculate_equal_splits(total_amount_cents, participant_ids)
    if split_type_upper == "PERCENTAGE":
        return _calculate_percentage_splits(total_amount_cents, percentages)
    if split_type_upper == "EXACT":
        return _calculate_exact_splits(total_amount_cents, exact_amounts)
    if split_type_upper == "WEIGHTED":
        return _calculate_weighted_splits(total_amount_cents, weights)

    raise SplitEngineError(
        f"Unsupported split type: '{split_type}'. Supported types: EQUAL, PERCENTAGE, EXACT, WEIGHTED."
    )
