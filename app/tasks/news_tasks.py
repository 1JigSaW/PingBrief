from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import logging

from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties
from sqlalchemy.orm import joinedload

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
    Source,
)
from app.repositories import users as users_repo
from app.repositories import subscriptions as subscriptions_repo
from bot.texts import PREMIUM_EXPIRED_MULTIPLE_SOURCES_TEXT
from bot.keyboards.builders import build_paywall_keyboard_with_keep_options
from app.services.i18n.translator import TranslatorService
from app.config import get_settings
from app.services.agents import SummarizerAgent, SummarizeInput

PREMIUM_EXPIRED_NOTICE_URL = "premium://expired-notice"


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
        users_all: List[User] = (
            db.query(User)
            .filter(User.telegram_id.is_not(None))
            .all()
        )
        eligible_source_ids: set = set()
        for u in users_all:
            subs_u: List[Subscription] = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == u.id,
                    Subscription.is_active.is_(True),
                )
                .all()
            )
            if not subs_u:
                continue
            is_eligible = users_repo.has_active_premium(
                telegram_id=str(u.telegram_id),
            ) or len(subs_u) <= 1
            if not is_eligible:
                continue
            for s in subs_u:
                eligible_source_ids.add(s.source_id)
        items = (
            db.query(NewsItem)
            .filter(NewsItem.summary.is_(None))
            .order_by(NewsItem.created_at.desc())
            .limit(limit)
            .all()
        )
        for ni in items:
            if ni.source_id not in eligible_source_ids:
                continue
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
        users_all: List[User] = (
            db.query(User)
            .filter(User.telegram_id.is_not(None))
            .all()
        )
        by_source_lang = {}
        for u in users_all:
            subs_u: List[Subscription] = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == u.id,
                    Subscription.is_active.is_(True),
                )
                .all()
            )
            if not subs_u:
                continue
            is_eligible = users_repo.has_active_premium(
                telegram_id=str(u.telegram_id),
            ) or len(subs_u) <= 1
            if not is_eligible:
                continue
            for s in subs_u:
                by_source_lang.setdefault(s.source_id, set()).add(s.language)

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
def notify_premium_expired(
    lookback_minutes: int = 1440,
) -> None:
    settings = get_settings()
    db = SessionLocalSync()
    try:
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=lookback_minutes)
        users = (
            db.query(User)
            .filter(
                User.telegram_id.is_not(None),
                User.premium_until.is_not(None),
                User.premium_until <= now,
                User.premium_until > window_start,
            )
            .all()
        )
        if not users:
            return
        bot = Bot(
            token=settings.telegram_bot_token,
            default=DefaultBotProperties(
                parse_mode="HTML",
            ),
        )
        try:
            for u in users:
                active_subs = (
                    db.query(Subscription)
                    .filter(
                        Subscription.user_id == u.id,
                        Subscription.is_active.is_(True),
                    )
                    .all()
                )
                if len(active_subs) <= 1:
                    continue
                already = (
                    db.query(Digest)
                    .filter(
                        Digest.user_id == u.id,
                        Digest.url == PREMIUM_EXPIRED_NOTICE_URL,
                        Digest.status == DigestStatus.SENT,
                        Digest.sent_at >= window_start,
                    )
                    .first()
                )
                if already:
                    continue
                # Build keyboard options by names
                source_ids = [sub.source_id for sub in active_subs]
                srcs = (
                    db.query(Source)
                    .filter(Source.id.in_(source_ids))
                    .all()
                )
                options = [
                    (s.name, str(s.id))
                    for s in srcs
                ]
                kb = build_paywall_keyboard_with_keep_options(
                    options=options,
                )
                async def _send_once():
                    await bot.send_message(
                        chat_id=int(u.telegram_id) if u.telegram_id.isdigit() else u.telegram_id,
                        text=PREMIUM_EXPIRED_MULTIPLE_SOURCES_TEXT,
                        disable_notification=False,
                        disable_web_page_preview=True,
                        reply_markup=kb.as_markup(),
                    )
                try:
                    asyncio.run(_send_once())
                    db.add(
                        Digest(
                            user_id=u.id,
                            subscription_id=active_subs[0].id,
                            title="Premium expired",
                            summary="",
                            url=PREMIUM_EXPIRED_NOTICE_URL,
                            scheduled_for=now,
                            sent_at=now,
                            status=DigestStatus.SENT,
                        )
                    )
                    db.commit()
                except Exception as e:
                    logging.getLogger(__name__).exception(
                        "notify_premium_expired_send_failed",
                        extra={"user": u.telegram_id, "error": str(e)},
                    )
        finally:
            async def _close():
                await bot.session.close()
            try:
                asyncio.run(_close())
            except Exception:
                pass
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
        # Load subscriptions for each user
        for user in users:
            user.subscriptions = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == user.id,
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
            keyboard = None,
        ) -> None:
            bot = Bot(
                token=settings.telegram_bot_token,
                default=DefaultBotProperties(
                    parse_mode="HTML",
                ),
            )
            try:
                for chat_id, text, silent in sends:
                    chat_id_val = int(chat_id) if isinstance(chat_id, str) and chat_id.isdigit() else chat_id
                    try:
                        await bot.send_message(
                            chat_id=chat_id_val,
                            text=text,
                            disable_notification=silent,
                            disable_web_page_preview=True,
                            reply_markup=keyboard.as_markup() if keyboard else None,
                        )
                    except Exception as e:
                        logging.getLogger(__name__).exception(
                            "send_message_failed",
                            extra={
                                "chat_id": chat_id,
                                "error": str(e),
                            },
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
            
            # Check premium status if user has multiple active sources
            if len(subs) > 1 and not users_repo.has_active_premium(
                telegram_id=telegram_id,
            ):
                # Premium expired - ensure we only notify ONCE per expiry window
                already_notified = (
                    db.query(Digest)
                    .filter(
                        Digest.user_id == (
                            db.query(User.id).filter(User.telegram_id == telegram_id).scalar_subquery()
                        ),
                        Digest.url == PREMIUM_EXPIRED_NOTICE_URL,
                        Digest.status == DigestStatus.SENT,
                        Digest.sent_at >= cutoff_min_ts,
                    )
                    .first()
                )
                if not already_notified:
                    # Build keyboard options from active subs
                    active_sources = [
                        (str(s.source_id), str(s.source_id))
                        for s in subs
                    ]
                    kb = build_paywall_keyboard_with_keep_options(
                        options=[
                            (str(s.source_id), str(s.source_id))
                            for s in subs
                        ],
                    )
                    asyncio.run(
                        _send_batch(
                            sends=[(telegram_id, PREMIUM_EXPIRED_MULTIPLE_SOURCES_TEXT, False)],
                            keyboard=kb,
                        ),
                    )
                    # Record notification digest
                    user_id_val = (
                        db.query(User.id).filter(User.telegram_id == telegram_id).scalar()
                    )
                    if user_id_val:
                        db.add(
                            Digest(
                                user_id=user_id_val,
                                subscription_id=subs[0].id,
                                title="Premium expired",
                                summary="",
                                url=PREMIUM_EXPIRED_NOTICE_URL,
                                scheduled_for=datetime.utcnow(),
                                sent_at=datetime.utcnow(),
                                status=DigestStatus.SENT,
                            )
                        )
                        db.commit()
                # Skip sending news until user chooses an option
                continue
            
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
    normalized_url = _normalize_url(
        url=url,
    )
    safe_url_attr = _escape_html_attr(
        text=normalized_url,
    )
    domain = _extract_domain(
        url=normalized_url,
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
        if not url:
            return "link"
        
        normalized = _normalize_url(
            url=url,
        )
        parsed = urlparse(normalized)
        host = parsed.netloc
        
        if not host:
            return "link"
            
        if host.startswith("www."):
            host = host[4:]
        
        if not _is_valid_host(host):
            return "link"

        return host
    except Exception:
        return "link"


def _normalize_url(
    url: str,
) -> str:
    val = (url or "").strip()
    if not val:
        return ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", val):
        return val
    return f"https://{val}"


def _is_valid_host(
    host: str,
) -> bool:
    try:
        h = (host or "").strip()
        if not h:
            return False

        if h == "localhost":
            return True

        # IPv6 in brackets
        if h.startswith("[") and h.endswith("]"):
            inner = h[1:-1]
            return True if re.fullmatch(r"[0-9a-fA-F:]+", inner or "") else False

        # IPv4 address
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", h or ""):
            parts = [int(p) for p in h.split(".")]
            return all(0 <= p <= 255 for p in parts)

        # Domain name must contain a dot and valid labels
        if "." not in h:
            return False

        labels = h.split(".")
        # TLD should be last label and at least 2 letters
        tld = labels[-1]
        if not re.fullmatch(r"[a-zA-Z]{2,}", tld):
            return False

        label_re = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$")
        for label in labels:
            if not label or len(label) > 63:
                return False
            if not label_re.fullmatch(label):
                return False

        return True
    except Exception:
        return False

