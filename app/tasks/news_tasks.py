from app.db.session import SessionLocalSync
from app.services.parsers.hackernews import HackerNewsParser
from app.services.parsers.techcrunch import TechCrunchParser
from app.worker.celery_app import celery_app
from app.db.session import SessionLocalSync
from app.db.models import NewsItem, Subscription
from app.services.i18n.translator import TranslatorService
from app.config import get_settings
from app.services.agents import SummarizerAgent, SummarizeInput


@celery_app.task(ignore_result=True)
def parse_hackernews(
    limit: int = 50,
):
    db = SessionLocalSync()
    try:
        parser = HackerNewsParser(
            db=db,
        )
        parser.save_new_sync(
            limit=limit,
        )
    finally:
        db.close()


@celery_app.task(ignore_result=True)
def parse_techcrunch(
    limit: int = 50,
):
    db = SessionLocalSync()
    try:
        parser = TechCrunchParser(
            db=db,
        )
        parser.save_new_sync(
            limit=limit,
        )
    finally:
        db.close()


@celery_app.task(ignore_result=True)
def summarize_fresh_news(
    limit: int = 200,
):
    db = SessionLocalSync()
    try:
        agent = SummarizerAgent()
        items = (
            db.query(NewsItem)
            .filter(NewsItem.summary.is_(None))
            .order_by(NewsItem.created_at.desc())
            .limit(limit)
            .all()
        )
        for ni in items:
            if not ni.content or len(ni.content.strip()) < 40:
                ni.summary = f"• {ni.title}\n• {ni.url}"
                continue
            summary = agent.summarize(
                payload=SummarizeInput(
                    title=ni.title,
                    content=ni.content,
                    url=ni.url,
                ),
                max_output_tokens=384,
                temperature=0.1,
                seed=42,
            )
            ni.summary = summary
        db.commit()
    finally:
        db.close()


@celery_app.task(ignore_result=True)
def translate_needed_summaries(
    limit: int = 500,
):
    settings = get_settings()
    db = SessionLocalSync()
    try:
        svc = TranslatorService(
            db=db,
            base_url="http://libretranslate:5000",
            timeout_seconds=10,
            provider_name="libretranslate",
        )
        active_subs = (
            db.query(Subscription.source_id, Subscription.language)
            .filter(Subscription.is_active.is_(True))
            .distinct()
            .all()
        )
        by_source_lang = {}
        for src_id, lang in active_subs:
            by_source_lang.setdefault(src_id, set()).add(lang)

        items = (
            db.query(NewsItem)
            .filter(NewsItem.summary.is_not(None))
            .order_by(NewsItem.created_at.desc())
            .limit(limit)
            .all()
        )
        for ni in items:
            langs = by_source_lang.get(ni.source_id) or set()
            for lang in langs:
                if lang == "en":
                    continue
                svc.translate_summary(
                    news_item=ni,
                    target_language=lang,
                )
    finally:
        db.close()

