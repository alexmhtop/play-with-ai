from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .entities import BookRecord
from .models import Book, CreateBook, UpdateBook


class BookService:
    def __init__(self, session: Session):
        self.session = session

    def reset(self) -> None:
        self.session.execute(text("TRUNCATE TABLE books RESTART IDENTITY CASCADE;"))
        self.session.commit()

    def list(self) -> list[Book]:
        records = self.session.execute(select(BookRecord)).scalars().all()
        return [self._to_schema(record) for record in records]

    def create(self, payload: CreateBook) -> Book:
        record = BookRecord(**payload.model_dump())
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self._to_schema(record)

    def get(self, book_id: int) -> Book:
        record = self.session.get(BookRecord, book_id)
        if record is None:
            raise KeyError(book_id)
        return self._to_schema(record)

    def update(self, book_id: int, payload: UpdateBook) -> Book:
        record = self.session.get(BookRecord, book_id)
        if record is None:
            raise KeyError(book_id)

        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(record, field, value)
        record.version += 1
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self._to_schema(record)

    def delete(self, book_id: int) -> None:
        record = self.session.get(BookRecord, book_id)
        if record is None:
            raise KeyError(book_id)
        self.session.delete(record)
        self.session.commit()

    @staticmethod
    def _to_schema(record: BookRecord) -> Book:
        return Book.model_validate(record, from_attributes=True)
