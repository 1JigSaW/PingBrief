from uuid import UUID
from typing import Dict, Set

_selection: Dict[int, Set[UUID]] = {}
_source_selection_context: Dict[int, str] = {}
_premium_users: Set[int] = set()

def get_selection(chat_id: int) -> Set[UUID]:
    return _selection.setdefault(chat_id, set())

def pop_selection(chat_id: int) -> Set[UUID]:
    return _selection.pop(chat_id, set())

def set_source_selection_context(chat_id: int, context: str) -> None:
    _source_selection_context[chat_id] = context

def get_source_selection_context(chat_id: int) -> str:
    return _source_selection_context.get(chat_id, "onboarding")

def clear_source_selection_context(chat_id: int) -> None:
    _source_selection_context.pop(chat_id, None)


def set_premium(
    user_id: int,
) -> None:
    _premium_users.add(user_id)


def is_premium(
    user_id: int,
) -> bool:
    return user_id in _premium_users
