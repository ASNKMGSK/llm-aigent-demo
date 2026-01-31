from collections import deque
from threading import Lock
from typing import Dict, List

# Settings
MAX_MEMORY_TURNS = 5

# Store
MEMORY_STORE: Dict[str, deque] = {}
MEMORY_LOCK = Lock()


def get_user_memory(username: str) -> deque:
    """사용자별 메모리 deque 반환"""
    if username not in MEMORY_STORE:
        MEMORY_STORE[username] = deque(maxlen=MAX_MEMORY_TURNS * 2)
    return MEMORY_STORE[username]


def memory_messages(username: str) -> List[Dict[str, str]]:
    """사용자의 대화 히스토리 반환"""
    with MEMORY_LOCK:
        return list(get_user_memory(username))


def append_memory(username: str, user_input: str, assistant_output: str) -> None:
    """대화 내용을 메모리에 추가"""
    with MEMORY_LOCK:
        mem = get_user_memory(username)
        mem.append({"role": "user", "content": user_input})
        mem.append({"role": "assistant", "content": assistant_output})


def clear_memory(username: str) -> None:
    """사용자의 메모리 초기화"""
    with MEMORY_LOCK:
        MEMORY_STORE[username] = deque(maxlen=MAX_MEMORY_TURNS * 2)
