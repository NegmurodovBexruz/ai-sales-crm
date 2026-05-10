from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.operator_deps import CurrentOperator
from app.models.product import Product

router = APIRouter(prefix="/operator/products", tags=["operator-products"])


class OperatorProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    category: str | None
    price: Decimal
    discount_price: Decimal | None
    stock_count: int
    availability_status: str
    image_url: str | None
    tags: str | None


@router.get("", response_model=list[OperatorProductRead])
def list_operator_products(db: DbSession, current_operator: CurrentOperator) -> list[Product]:
    return list(
        db.scalars(
            select(Product)
            .where(Product.business_id == current_operator.business_id)
            .order_by(Product.name.asc())
        ).all()
    )
