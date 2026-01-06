from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from . import station
from . import user

__all__ = ["Base", "station", "user"]

__all__ = ["Station", "User", "Base"]
