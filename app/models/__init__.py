from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from .station import Station
from .user import User

__all__ = ["Station", "User", "Base"]
