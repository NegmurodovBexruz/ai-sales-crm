from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.access import get_accessible_business_ids, require_business_admin_or_owner
from app.api.deps import CurrentUser, DbSession
from app.models.order import Order, OrderItem
from app.schemas.order import OrderDoneResponse, OrderRead, OrderStatusUpdate
from app.services.order_service import (
    InsufficientStockError,
    OrderBusinessMismatchError,
    OrderNotFoundError,
    cancel_order,
    mark_order_done,
)
from app.services.operator_assignment_service import cancel_assignment_by_order, complete_assignment_by_order

router = APIRouter(prefix="/orders", tags=["orders"])


def get_accessible_order(db: DbSession, order_id: int, current_user: CurrentUser) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    require_business_admin_or_owner(db, current_user, order.business_id)
    return order


@router.get("", response_model=list[OrderRead])
def list_orders(db: DbSession, current_user: CurrentUser, business_id: int | None = None) -> list[Order]:
    accessible_ids = get_accessible_business_ids(db, current_user)
    query = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).order_by(Order.created_at.desc())
    if business_id is not None:
        require_business_admin_or_owner(db, current_user, business_id)
        query = query.where(Order.business_id == business_id)
    elif accessible_ids is not None:
        if not accessible_ids:
            return []
        query = query.where(Order.business_id.in_(accessible_ids))
    return list(db.scalars(query).all())


@router.patch("/{order_id}/done", response_model=OrderDoneResponse)
def complete_order(order_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    accessible_order = get_accessible_order(db, order_id, current_user)
    already_done = accessible_order.status == "done"
    try:
        order = mark_order_done(db, order_id, business_id=accessible_order.business_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except OrderBusinessMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    complete_assignment_by_order(db, order.id)
    return {
        "order": order,
        "product_stock_count": None,
        "message": "Order already done." if already_done else f"Order #{order.id} done. Stock updated.",
    }


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Order:
    order = get_accessible_order(db, order_id, current_user)
    if payload.status not in {"new", "done", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported order status")

    if payload.status == "done":
        try:
            order = mark_order_done(db, order_id, business_id=order.business_id)
        except InsufficientStockError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        complete_assignment_by_order(db, order.id)
        return order

    if payload.status == "cancelled":
        order = cancel_order(db, order_id, business_id=order.business_id)
        cancel_assignment_by_order(db, order.id)
        return order

    if order.status != "done":
        order.status = "new"
        db.commit()
        db.refresh(order)
    return order
