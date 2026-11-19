import json

from sqlalchemy.orm import Session as DatabaseSession

from .config import settings
from .database import Session
from .models import Problem, StarterCode
from .schemas import ProblemDetail


def seed(db: DatabaseSession) -> int:
    entries = [ProblemDetail.model_validate(item) for item in json.loads(settings().seed_file.read_text())]
    for entry in entries:
        db.merge(Problem(
            **entry.model_dump(exclude={"starters"}),
            starters=[StarterCode(**starter.model_dump()) for starter in entry.starters],
        ))
    db.commit()
    return len(entries)


if __name__ == "__main__":
    with Session() as db:
        print(f"Seeded {seed(db)} problems")
