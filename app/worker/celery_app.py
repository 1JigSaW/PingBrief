from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "app",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=["app.tasks.hn_tasks"],
)

celery_app.conf.beat_schedule = {
    "hn-every-minute": {
        "task": "app.tasks.hn_tasks.parse_hackernews",
        "schedule": 60.0,
        "args": (50,),
    },
}
