from typing import Optional

from pydantic import BaseModel, Field


class Book(BaseModel):
    id: int
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=200)
    price: float
    in_stock: bool = True
    version: int = 1


class CreateBook(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0, lt=100000)
    in_stock: bool = True


class UpdateBook(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    author: Optional[str] = Field(default=None, min_length=1, max_length=200)
    price: Optional[float] = Field(default=None, gt=0, lt=100000)
    in_stock: Optional[bool] = None
