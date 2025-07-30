from app.db.session import SessionLocalSync
from app.services.parsers.hackernews import HackerNewsParser
from app.worker.celery_app import celery_app

@celery_app.task(ignore_result=True)
def parse_hackernews(limit: int = 50):
    db = SessionLocalSync()
    try:
        parser = HackerNewsParser(db)
        parser.save_new_sync(limit)
    finally:
        db.close()
