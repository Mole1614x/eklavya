from collections.abc import Callable
from typing import Annotated

from celery import Celery
from fastapi import Depends

from .config import settings

client = Celery("eklavya-api", broker=settings().redis_url)


def enqueue_submission(submission_id: str) -> None:
    client.send_task("judge.evaluate", args=[submission_id])


def get_enqueuer() -> Callable[[str], None]:
    return enqueue_submission


Enqueuer = Annotated[Callable[[str], None], Depends(get_enqueuer)]
