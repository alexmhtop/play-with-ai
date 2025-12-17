from sqlalchemy import Boolean, Column, Float, Integer, String

from .db import Base


class BookRecord(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    author = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    in_stock = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
