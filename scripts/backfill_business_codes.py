import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select  # noqa: E402

from backend.app.db.session import SessionLocal  # noqa: E402
from backend.app.models.business import Business  # noqa: E402
from backend.app.utils.business_ids import (  # noqa: E402
    generate_admin_join_code,
    generate_operator_code,
    generate_public_business_id,
)


def main() -> None:
    db = SessionLocal()
    try:
        businesses = list(
            db.scalars(
                select(Business).where(
                    (Business.public_business_id.is_(None))
                    | (Business.admin_join_code.is_(None))
                    | (Business.operator_code.is_(None))
                )
            ).all()
        )
        updated_count = 0
        for business in businesses:
            changed = False
            if not business.public_business_id:
                business.public_business_id = generate_public_business_id(db)
                changed = True
            if not business.admin_join_code:
                business.admin_join_code = generate_admin_join_code(db)
                changed = True
            if not business.operator_code:
                business.operator_code = generate_operator_code(db)
                changed = True
            if changed:
                updated_count += 1
        db.commit()
        print(f"Updated businesses: {updated_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
