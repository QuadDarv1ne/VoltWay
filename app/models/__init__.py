from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models to ensure they are registered with Base
from . import station  # noqa: F401
from . import user  # noqa: F401
from . import favorite  # noqa: F401
from . import api_key  # noqa: F401
from . import audit_log  # noqa: F401
from . import review  # noqa: F401
from . import reservation  # noqa: F401
from . import coupon  # noqa: F401

__all__ = ["Base", "station", "user", "favorite", "api_key", "audit_log", "review", "reservation", "coupon"]
