from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties

from app.db.session import SessionLocalSync
from app.services.parsers.hackernews import HackerNewsParser
from app.services.parsers.techcrunch import TechCrunchParser
from app.services.parsers.generic_rss import GenericRssParser
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
def parse_theverge(
    limit: int = 50,
):
    db = SessionLocalSync()
    try:
        parser = GenericRssParser(
            db=db,
            source_name="The Verge",
            feed_url="https://www.theverge.com/rss/index.xml",
            default_language="en",
        )
        parser.save_new_sync(
            limit=limit,
        )
    finally:
        db.close()


@celery_app.task(ignore_result=True)
def parse_engadget(
    limit: int = 50,
):
    db = SessionLocalSync()
    try:
        parser = GenericRssParser(
            db=db,
            source_name="Engadget",
            feed_url="https://www.engadget.com/rss.xml",
            default_language="en",
        )
        parser.save_new_sync(
            limit=limit,
        )
    finally:
        db.close()


@celery_app.task(ignore_result=True)
def parse_wired(
    limit: int = 50,
):
    db = SessionLocalSync()
    try:
        parser = GenericRssParser(
            db=db,
            source_name="WIRED",
            feed_url="https://www.wired.com/feed/rss",
            default_language="en",
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
    max_backlog_hours: int = 48,
    max_messages_per_chat_per_run: int = 3,
    batch_threshold: int = 3,
):
    """Send fresh news per subscription with cursor-based delivery.
    """
    settings = get_settings()
    db = SessionLocalSync()
    try:
        now_ts = datetime.utcnow()
        cutoff_min_ts = now_ts - timedelta(
            hours=max_backlog_hours,
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
                        disable_web_page_preview=True,
                    )
                    await asyncio.sleep(
                        0.25,
                    )
            finally:
                await bot.session.close()

        sends_plan: List[Tuple[str, str, bool]] = []
        per_chat_sent_in_batch: Dict[str, int] = {}

        for telegram_id, subs in user_id_to_active_subs.items():
            chat_budget = per_chat_sent_in_batch.get(
                telegram_id,
                0,
            )
            for sub in subs:
                if chat_budget >= max_messages_per_chat_per_run:
                    break

                last_digest: Optional[Digest] = (
                    db.query(Digest)
                    .filter(
                        Digest.subscription_id == sub.id,
                        Digest.status == DigestStatus.SENT,
                    )
                    .order_by(
                        Digest.sent_at.desc(),
                    )
                    .first()
                )
                last_sent_at = last_digest.sent_at if last_digest and last_digest.sent_at else cutoff_min_ts

                items: List[NewsItem] = (
                    db.query(NewsItem)
                    .filter(
                        NewsItem.source_id == sub.source_id,
                        NewsItem.is_active.is_(True),
                        NewsItem.fetched_at > last_sent_at,
                        NewsItem.fetched_at >= cutoff_min_ts,
                        NewsItem.summary.is_not(None),
                    )
                    .order_by(
                        NewsItem.fetched_at.asc(),
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

                if len(new_items) < batch_threshold:
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
                        if count >= max_messages_per_chat_per_run:
                            break
                        sends_plan.append(
                            (
                                telegram_id,
                                message_text,
                                True if count >= 1 else False,
                            ),
                        )
                        per_chat_sent_in_batch[telegram_id] = count + 1
                        chat_budget = per_chat_sent_in_batch[telegram_id]
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
                    if count >= max_messages_per_chat_per_run:
                        continue
                    sends_plan.append(
                        (
                            telegram_id,
                            message_text,
                            True if count >= 1 else False,
                        ),
                    )
                    per_chat_sent_in_batch[telegram_id] = count + 1
                    chat_budget = per_chat_sent_in_batch[telegram_id]

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


def _escape_html_attr(
    text: str,
) -> str:
    return (
        text
        .replace(
            "&",
            "&amp;",
        )
        .replace(
            '"',
            "&quot;",
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
    concise = _shorten_summary(
        text=summary or "",
        max_sentences=2,
        max_chars=300,
    )
    safe_summary = _escape_html(
        text=concise,
    )
    safe_url_attr = _escape_html_attr(
        text=url,
    )
    domain = _extract_domain(
        url=url,
    )
    safe_domain = _escape_html(
        text=domain,
    )
    return "\n".join(
        [
            f"📰 <b>{safe_title}</b>",
            f"{safe_summary}",
            f'↗️ <a href="{safe_url_attr}">{safe_domain}</a>',
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


def _shorten_summary(
    text: str,
    max_sentences: int = 2,
    max_chars: int = 300,
) -> str:
    content = (text or "").strip()
    if not content:
        return ""
    # Split by sentence boundaries.
    sentences = re.split(
        pattern=r"(?<=[\.!?])\s+",
        string=content,
    )
    picked = " ".join(
        sentences[: max(1, max_sentences)],
    ).strip()
    if len(picked) > max_chars:
        return picked[: max_chars - 1].rstrip() + "…"
    return picked


def _extract_domain(
    url: str,
) -> str:
    try:
        parsed = urlparse(url or "")
        host = parsed.netloc or "link"
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return "link"

