from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.lead import Lead
from app.models.order import Order, OrderItem
from app.models.product import Product


class OrderServiceError(Exception):
    pass


class OrderNotFoundError(OrderServiceError):
    pass


class InsufficientStockError(OrderServiceError):
    pass


class OrderBusinessMismatchError(OrderServiceError):
    pass


def create_order(
    db: Session,
    business_id: int,
    customer_id: int,
    product_id: int,
    quantity: int,
    total_price: Decimal,
    customer_name: str,
    phone: str,
    address: str,
    comment: str | None = None,
) -> Order:
    order = Order(
        business_id=business_id,
        customer_id=customer_id,
        product_id=product_id,
        quantity=quantity,
        total_price=total_price,
        customer_name=customer_name,
        phone=phone,
        address=address,
        comment=comment,
        status="new",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def create_order_with_items(
    db: Session,
    business_id: int,
    customer_id: int,
    customer_name: str,
    phone: str,
    address: str,
    comment: str | None,
    items: list[dict],
) -> Order:
    if not items:
        raise OrderServiceError("Order must contain at least one item")

    requested_quantities: dict[int, int] = {}
    for item in items:
        product_id = int(item["product_id"])
        quantity = int(item["quantity"])
        if quantity <= 0:
            raise OrderServiceError("Item quantity must be positive")
        requested_quantities[product_id] = requested_quantities.get(product_id, 0) + quantity

    product_ids = list(requested_quantities)
    products = {
        product.id: product
        for product in db.scalars(
            select(Product).where(Product.id.in_(product_ids), Product.business_id == business_id)
        ).all()
    }

    normalized_items: list[dict] = []
    total_price = Decimal("0")
    for product_id, quantity in requested_quantities.items():
        product = products.get(product_id)
        if product is None:
            raise OrderServiceError("Product not found for this business")
        if product.stock_count <= 0:
            raise InsufficientStockError(f"{product.name} is out of stock")
        if quantity > product.stock_count:
            raise InsufficientStockError(f"Not enough stock for {product.name}")
        final_unit_price = product.discount_price if product.discount_price is not None else product.price
        item_total = final_unit_price * quantity
        total_price += item_total
        normalized_items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": product.price,
                "discount_price": product.discount_price,
                "final_unit_price": final_unit_price,
                "total_price": item_total,
            }
        )

    first_item = normalized_items[0]
    order = Order(
        business_id=business_id,
        customer_id=customer_id,
        product_id=first_item["product"].id,
        quantity=first_item["quantity"],
        total_price=total_price,
        customer_name=customer_name,
        phone=phone,
        address=address,
        comment=comment,
        status="new",
    )
    db.add(order)
    db.flush()
    for item in normalized_items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=item["product"].id,
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                discount_price=item["discount_price"],
                final_unit_price=item["final_unit_price"],
                total_price=item["total_price"],
            )
        )
    db.commit()
    return get_order_with_items(db, order.id) or order


def get_order_with_items(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )


def get_order_stock_items(order: Order) -> list[tuple[int, int]]:
    if order.items:
        return [(item.product_id, item.quantity) for item in order.items]
    if order.product_id is not None and order.quantity is not None:
        return [(order.product_id, order.quantity)]
    return []


def mark_order_done(db: Session, order_id: int, business_id: int | None = None) -> Order:
    order = get_order_with_items(db, order_id)
    if order is None:
        raise OrderNotFoundError("Order not found")
    if business_id is not None and order.business_id != business_id:
        raise OrderBusinessMismatchError("Order does not belong to this business")
    if order.status == "done":
        return order

    stock_items = get_order_stock_items(order)
    if not stock_items:
        raise OrderServiceError("Order has no items")
    products = {
        product.id: product
        for product in db.scalars(
            select(Product).where(Product.id.in_([product_id for product_id, _ in stock_items]))
        ).all()
    }
    for product_id, quantity in stock_items:
        product = products.get(product_id)
        if product is None:
            raise OrderServiceError("Order product not found")
        if product.stock_count < quantity:
            raise InsufficientStockError(f"Not enough stock for {product.name}")

    for product_id, quantity in stock_items:
        products[product_id].stock_count -= quantity
    order.status = "done"

    for product_id, _ in stock_items:
        lead = db.scalar(
            select(Lead).where(
                Lead.business_id == order.business_id,
                Lead.customer_id == order.customer_id,
                Lead.interested_product_id == product_id,
                Lead.status != "done",
            )
        )
        if lead is not None:
            lead.status = "done"

    db.commit()
    refreshed_order = get_order_with_items(db, order.id)
    return refreshed_order or order


def cancel_order(db: Session, order_id: int, business_id: int | None = None) -> Order:
    order = db.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise OrderNotFoundError("Order not found")
    if business_id is not None and order.business_id != business_id:
        raise OrderBusinessMismatchError("Order does not belong to this business")
    if order.status != "done":
        order.status = "cancelled"
        db.commit()
        db.refresh(order)
    return order
