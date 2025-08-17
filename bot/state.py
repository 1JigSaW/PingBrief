from uuid import UUID
from typing import Dict, Set

_selection: Dict[int, Set[UUID]] = {}
_source_selection_context: Dict[int, str] = {}
_last_selected_source: Dict[int, UUID] = {}

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


def set_last_selected_source(
    chat_id: int,
    source_id: UUID,
) -> None:
    _last_selected_source[chat_id] = source_id


def get_last_selected_source(
    chat_id: int,
) -> UUID | None:
    return _last_selected_source.get(chat_id)


def clear_last_selected_source(
    chat_id: int,
) -> None:
    _last_selected_source.pop(chat_id, None)
