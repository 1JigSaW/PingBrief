from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties

from app.db.session import SessionLocalSync
from app.services.parsers.hackernews import HackerNewsParser
from app.services.parsers.techcrunch import TechCrunchParser
from app.worker.celery_app import celery_app
from app.db.session import SessionLocalSync
from app.db.models import (
    NewsItem,
    Subscription,
    User,
    Digest,
    DigestStatus,
    NewsItemTranslation,
)
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
                ni.summary = f"{ni.title}\n{ni.url}"
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


@celery_app.task(ignore_result=True)
def dispatch_news_updates(
    window_minutes: int = 5,
    max_items_per_subscription: int = 5,
    fallback_to_en_if_missing: bool = False,
):
    """Send fresh news per subscription.

    - 1–2 items → per-item messages with small pacing;
    - 3+ items → one batch message;
    - Language strictly equals subscription language; optional EN fallback.
    """
    settings = get_settings()
    db = SessionLocalSync()
    try:
        since_ts = datetime.utcnow() - timedelta(
            minutes=window_minutes,
        )

        users: List[User] = (
            db.query(User)
            .filter(
                User.telegram_id.is_not(None),
            )
            .all()
        )

        user_id_to_active_subs: Dict[str, List[Subscription]] = {}
        for u in users:
            active_subs = [
                sub
                for sub in (u.subscriptions or [])
                if sub.is_active
            ]
            if active_subs:
                user_id_to_active_subs[str(u.telegram_id)] = active_subs

        async def _send_batch(
            sends: List[Tuple[str, str, bool]],
        ) -> None:
            bot = Bot(
                token=settings.telegram_bot_token,
                default=DefaultBotProperties(
                    parse_mode="HTML",
                ),
            )
            try:
                for chat_id, text, silent in sends:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        disable_notification=silent,
                    )
                    await asyncio.sleep(
                        0.25,
                    )
            finally:
                await bot.session.close()

        sends_plan: List[Tuple[str, str, bool]] = []
        per_chat_sent_in_batch: Dict[str, int] = {}

        for telegram_id, subs in user_id_to_active_subs.items():
            for sub in subs:
                items: List[NewsItem] = (
                    db.query(NewsItem)
                    .filter(
                        NewsItem.source_id == sub.source_id,
                        NewsItem.is_active.is_(True),
                        NewsItem.fetched_at >= since_ts,
                        NewsItem.summary.is_not(None),
                    )
                    .order_by(
                        NewsItem.fetched_at.desc(),
                    )
                    .limit(
                        max_items_per_subscription,
                    )
                    .all()
                )
                if not items:
                    continue

                sent_urls = {
                    d.url
                    for d in (
                        db.query(Digest)
                        .filter(
                            Digest.subscription_id == sub.id,
                            Digest.status == DigestStatus.SENT,
                        )
                        .all()
                    )
                }
                new_items = [
                    ni
                    for ni in items
                    if ni.url not in sent_urls
                ]
                if not new_items:
                    continue

                # 1–2 per-item, else batch
                if len(new_items) <= 2:
                    for ni in new_items:
                        summ = _pick_summary_for_lang(
                            db=db,
                            item=ni,
                            lang=sub.language,
                            fallback_to_en=fallback_to_en_if_missing,
                        )
                        if not summ:
                            continue
                        message_text = _render_single_message(
                            title=ni.title,
                            summary=summ,
                            url=ni.url,
                        )
                        count = per_chat_sent_in_batch.get(
                            telegram_id,
                            0,
                        )
                        sends_plan.append(
                            (
                                telegram_id,
                                message_text,
                                True if count >= 1 else False,
                            ),
                        )
                        per_chat_sent_in_batch[telegram_id] = count + 1
                        _record_digest(
                            db=db,
                            sub=sub,
                            item=ni,
                            summary=summ,
                        )
                else:
                    blocks: List[str] = []
                    for ni in new_items:
                        summ = _pick_summary_for_lang(
                            db=db,
                            item=ni,
                            lang=sub.language,
                            fallback_to_en=fallback_to_en_if_missing,
                        )
                        if not summ:
                            continue
                        blocks.append(
                            _render_item_block(
                                title=ni.title,
                                summary=summ,
                                url=ni.url,
                            ),
                        )
                        _record_digest(
                            db=db,
                            sub=sub,
                            item=ni,
                            summary=summ,
                        )
                    if not blocks:
                        continue
                    message_text = "\n\n".join(
                        blocks,
                    )
                    count = per_chat_sent_in_batch.get(
                        telegram_id,
                        0,
                    )
                    sends_plan.append(
                        (
                            telegram_id,
                            message_text,
                            True if count >= 1 else False,
                        ),
                    )
                    per_chat_sent_in_batch[telegram_id] = count + 1

        if sends_plan:
            asyncio.run(
                _send_batch(
                    sends=sends_plan,
                ),
            )
        db.commit()
    finally:
        db.close()


def _escape_html(
    text: str,
) -> str:
    return (
        text
        .replace(
            "&",
            "&amp;",
        )
        .replace(
            "<",
            "&lt;",
        )
        .replace(
            ">",
            "&gt;",
        )
    )


def _render_single_message(
    title: str,
    summary: str,
    url: str,
) -> str:
    safe_title = _escape_html(
        text=title,
    )
    safe_summary = _escape_html(
        text=(summary or "")[:900],
    )
    return "\n".join(
        [
            f"🆕 <b>{safe_title}</b>",
            safe_summary,
            f"🔗 {url}",
        ]
    )


def _render_item_block(
    title: str,
    summary: str,
    url: str,
) -> str:
    return _render_single_message(
        title=title,
        summary=summary,
        url=url,
    )


def _record_digest(
    db,
    sub: Subscription,
    item: NewsItem,
    summary: str,
) -> None:
    digest = Digest(
        user_id=sub.user_id,
        subscription_id=sub.id,
        title=item.title,
        summary=summary or "",
        url=item.url,
        scheduled_for=datetime.utcnow(),
        sent_at=datetime.utcnow(),
        status=DigestStatus.SENT,
    )
    db.add(
        digest,
    )


def _pick_summary_for_lang(
    db,
    item: NewsItem,
    lang: str,
    fallback_to_en: bool,
) -> Optional[str]:
    if lang == "en":
        return (item.summary or "").strip() or None
    tr: Optional[NewsItemTranslation] = (
        db.query(NewsItemTranslation)
        .filter(
            NewsItemTranslation.news_item_id == item.id,
            NewsItemTranslation.language == lang,
        )
        .one_or_none()
    )
    if tr and tr.summary_translated:
        return tr.summary_translated.strip()
    if fallback_to_en:
        return (item.summary or "").strip() or None
    return None

