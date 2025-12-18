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
    title: str | None = Field(default=None, min_length=1, max_length=200)
    author: str | None = Field(default=None, min_length=1, max_length=200)
    price: float | None = Field(default=None, gt=0, lt=100000)
    in_stock: bool | None = None
