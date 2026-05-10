from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operator_assignment import OperatorAssignment


def utc_now():
    return datetime.now(timezone.utc)


def get_active_assignment(db: Session, business_id: int, customer_id: int) -> OperatorAssignment | None:
    return db.scalar(
        select(OperatorAssignment).where(
            OperatorAssignment.business_id == business_id,
            OperatorAssignment.customer_id == customer_id,
            OperatorAssignment.status == "active",
        )
    )


def create_assignment(
    db: Session,
    business_id: int,
    customer_id: int,
    operator_id: int,
    order_id: int | None = None,
) -> OperatorAssignment:
    existing = get_active_assignment(db, business_id, customer_id)
    if existing is not None:
        if order_id is not None and existing.order_id is None:
            existing.order_id = order_id
            db.commit()
            db.refresh(existing)
        return existing

    assignment = OperatorAssignment(
        business_id=business_id,
        customer_id=customer_id,
        operator_id=operator_id,
        order_id=order_id,
        status="active",
        assigned_at=utc_now(),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def release_assignment(db: Session, assignment_id: int) -> OperatorAssignment | None:
    assignment = db.scalar(select(OperatorAssignment).where(OperatorAssignment.id == assignment_id))
    if assignment is None:
        return None
    assignment.status = "released"
    assignment.released_at = utc_now()
    db.commit()
    db.refresh(assignment)
    return assignment


def complete_assignment_by_order(db: Session, order_id: int) -> OperatorAssignment | None:
    assignment = db.scalar(
        select(OperatorAssignment).where(
            OperatorAssignment.order_id == order_id,
            OperatorAssignment.status == "active",
        )
    )
    if assignment is None:
        return None
    assignment.status = "done"
    assignment.done_at = utc_now()
    db.commit()
    db.refresh(assignment)
    return assignment


def complete_assignment_by_customer(db: Session, business_id: int, customer_id: int) -> OperatorAssignment | None:
    assignment = get_active_assignment(db, business_id, customer_id)
    if assignment is None:
        return None
    assignment.status = "done"
    assignment.done_at = utc_now()
    db.commit()
    db.refresh(assignment)
    return assignment


def cancel_assignment_by_order(db: Session, order_id: int) -> OperatorAssignment | None:
    assignment = db.scalar(
        select(OperatorAssignment).where(
            OperatorAssignment.order_id == order_id,
            OperatorAssignment.status == "active",
        )
    )
    if assignment is None:
        return None
    assignment.status = "cancelled"
    assignment.released_at = utc_now()
    db.commit()
    db.refresh(assignment)
    return assignment
