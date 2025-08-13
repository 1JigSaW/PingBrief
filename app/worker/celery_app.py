from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "app",
    broker=settings.broker_url,
    backend=settings.result_backend,
    include=[
        "app.tasks.news_tasks",
    ],
)

celery_app.conf.beat_schedule = {
    "techcrunch-every-5-minutes": {
        "task": "app.tasks.news_tasks.parse_techcrunch",
        "schedule": 60.0,
        "args": (
            50,
        ),
    },
    "hn-every-5-minutes": {
        "task": "app.tasks.news_tasks.parse_hackernews",
        "schedule": 300.0,
        "args": (
            50,
        ),
    },
}
