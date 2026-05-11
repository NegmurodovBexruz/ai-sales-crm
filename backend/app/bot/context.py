from contextvars import ContextVar, Token


_business_id: ContextVar[int | None] = ContextVar("telegram_business_id", default=None)


def set_telegram_business_id(business_id: int) -> Token[int | None]:
    return _business_id.set(business_id)


def reset_telegram_business_id(token: Token[int | None]) -> None:
    _business_id.reset(token)


def get_telegram_business_id() -> int | None:
    return _business_id.get()
