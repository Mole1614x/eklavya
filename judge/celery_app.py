from celery import Celery

from backend.app.config import settings

app = Celery("eklavya-judge", broker=settings().redis_url, backend=settings().redis_url)
app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
)
app.autodiscover_tasks(["judge"])
