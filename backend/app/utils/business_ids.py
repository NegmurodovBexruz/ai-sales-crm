import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business

ALPHABET = string.ascii_uppercase + string.digits


def generate_unique_business_code(db: Session, prefix: str, field_name: str) -> str:
    for _ in range(20):
        suffix = "".join(secrets.choice(ALPHABET) for _ in range(6))
        code = f"{prefix}-{suffix}"
        exists = db.scalar(select(Business.id).where(getattr(Business, field_name) == code))
        if exists is None:
            return code
    raise RuntimeError(f"Could not generate unique business {field_name}")


def generate_public_business_id(db: Session) -> str:
    return generate_unique_business_code(db, "BIZ", "public_business_id")


def generate_admin_join_code(db: Session) -> str:
    return generate_unique_business_code(db, "ADM", "admin_join_code")


def generate_operator_code(db: Session) -> str:
    return generate_unique_business_code(db, "OP", "operator_code")
