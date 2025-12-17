import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from src.models import CreateBook, UpdateBook


@given(st.floats(max_value=0, allow_nan=False, allow_infinity=False))
def test_create_book_rejects_non_positive_price(price):
    with pytest.raises(ValidationError):
        CreateBook(title="t", author="a", price=price, in_stock=True)


@given(st.floats(min_value=0, max_value=0, allow_nan=False, allow_infinity=False))
def test_update_book_rejects_zero_price(price):
    with pytest.raises(ValidationError):
        UpdateBook(price=price)


def test_create_book_accepts_positive_price():
    book = CreateBook(title="ok", author="a", price=1.23)
    assert book.price == 1.23


def test_create_book_enforces_length():
    long_title = "t" * 201
    with pytest.raises(ValidationError):
        CreateBook(title=long_title, author="a", price=1.0)
