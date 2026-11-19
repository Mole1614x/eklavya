from collections.abc import Iterator

from sqlalchemy.orm import Session as DatabaseSession

from .database import Session


def get_db() -> Iterator[DatabaseSession]:
    with Session() as session:
        yield session
