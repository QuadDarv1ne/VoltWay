from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from . import Base
from datetime import datetime

class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    address = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    connector_type = Column(String)  # CCS, CHAdeMO, Type 2
    power_kw = Column(Float)
    status = Column(String)  # available, occupied, etc.
    price = Column(Float, nullable=True)
    hours = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)