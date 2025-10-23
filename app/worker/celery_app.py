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
        "schedule": 200.0,
        "args": (
            50,
        ),
    },
    "hn-every-5-minutes": {
        "task": "app.tasks.news_tasks.parse_hackernews",
        "schedule": 200.0,
        "args": (
            50,
        ),
    },
    "summarize-every-5-minutes": {
        "task": "app.tasks.news_tasks.summarize_fresh_news",
        "schedule": 200.0,
        "args": (
            200,
        ),
    },
    "theverge-every-5-minutes": {
        "task": "app.tasks.news_tasks.parse_theverge",
        "schedule": 300.0,
        "args": (
            50,
        ),
    },
    "engadget-every-5-minutes": {
        "task": "app.tasks.news_tasks.parse_engadget",
        "schedule": 300.0,
        "args": (
            50,
        ),
    },
    "wired-every-5-minutes": {
        "task": "app.tasks.news_tasks.parse_wired",
        "schedule": 300.0,
        "args": (
            50,
        ),
    },
    "translate-every-5-minutes": {
        "task": "app.tasks.news_tasks.translate_needed_summaries",
        "schedule": 200.0,
        "args": (
            500,
        ),
    },
    "dispatch-every-5-minutes": {
        "task": "app.tasks.news_tasks.dispatch_news_updates",
        "schedule": 200.0,
        "kwargs": {
            "window_minutes": 5,
            "max_items_per_subscription": 5,
            "fallback_to_en_if_missing": False,
            "max_backlog_hours": 48,
            "max_messages_per_chat_per_run": 3,
            "batch_threshold": 3,
        },
    },
    "notify-premium-expired-every-2-minutes": {
        "task": "app.tasks.news_tasks.notify_premium_expired",
        "schedule": 120.0,
        "args": (
            10,
        ),
    },
}
