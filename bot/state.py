from uuid import UUID
from typing import Dict, Set

_selection: Dict[int, Set[UUID]] = {}

def get_selection(chat_id: int) -> Set[UUID]:
    return _selection.setdefault(chat_id, set())

def pop_selection(chat_id: int) -> Set[UUID]:
    return _selection.pop(chat_id, set())
