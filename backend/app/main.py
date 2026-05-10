from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    ai,
    analytics,
    auth,
    business_members,
    businesses,
    conversations,
    customers,
    leads,
    operator_auth,
    operator_products,
    orders,
    operators,
    products,
    super_admin,
    telegram,
)
from app.core.config import settings

app = FastAPI(
    title="AI Sales CRM API",
    debug=settings.APP_DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(operator_auth.router, prefix="/api")
app.include_router(super_admin.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(businesses.router, prefix="/api")
app.include_router(business_members.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(operator_products.router, prefix="/api")
app.include_router(customers.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(operators.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(telegram.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}
