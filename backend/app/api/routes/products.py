from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.api.access import get_accessible_business_ids, require_business_admin_or_owner
from app.api.deps import CurrentUser, DbSession
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate, StockChange

router = APIRouter(prefix="/products", tags=["products"])


def get_accessible_product(db: DbSession, product_id: int, current_user: CurrentUser) -> Product:
    product = db.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_business_admin_or_owner(db, current_user, product.business_id)
    return product


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, current_user: CurrentUser) -> Product:
    require_business_admin_or_owner(db, current_user, payload.business_id)
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductRead])
def list_products(db: DbSession, current_user: CurrentUser, business_id: int | None = None) -> list[Product]:
    accessible_ids = get_accessible_business_ids(db, current_user)
    query = select(Product)
    if business_id is not None:
        require_business_admin_or_owner(db, current_user, business_id)
        query = query.where(Product.business_id == business_id)
    elif accessible_ids is not None:
        if not accessible_ids:
            return []
        query = query.where(Product.business_id.in_(accessible_ids))
    return list(db.scalars(query).all())


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: DbSession, current_user: CurrentUser) -> Product:
    return get_accessible_product(db, product_id, current_user)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Product:
    product = get_accessible_product(db, product_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession, current_user: CurrentUser) -> None:
    product = get_accessible_product(db, product_id, current_user)
    db.delete(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product cannot be deleted because it is used in existing orders.",
        ) from exc


@router.patch("/{product_id}/stock/increase", response_model=ProductRead)
def increase_stock(
    product_id: int,
    payload: StockChange,
    db: DbSession,
    current_user: CurrentUser,
) -> Product:
    product = get_accessible_product(db, product_id, current_user)
    product.stock_count += payload.amount
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}/stock/decrease", response_model=ProductRead)
def decrease_stock(
    product_id: int,
    payload: StockChange,
    db: DbSession,
    current_user: CurrentUser,
) -> Product:
    product = get_accessible_product(db, product_id, current_user)
    if product.stock_count - payload.amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock count cannot go below 0",
        )
    product.stock_count -= payload.amount
    db.commit()
    db.refresh(product)
    return product
