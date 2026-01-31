"""
state.py - 전역 상태 관리
모든 공유 가변 상태를 한 곳에서 관리합니다.
"""
import os
import logging
from typing import Dict, List, Any, Optional
from threading import Lock
from collections import deque

import pandas as pd

# ============================================================
# 경로
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "backend.log")

# ============================================================
# 로깅
# ============================================================
def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8", delay=True),
        ],
        force=True,
    )
    lg = logging.getLogger("demollm")
    lg.setLevel(logging.INFO)
    lg.propagate = True
    for uvn in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        ul = logging.getLogger(uvn)
        ul.setLevel(logging.INFO)
        ul.propagate = True
    lg.info("LOGGER_READY log_file=%s", LOG_FILE)
    return lg

logger = setup_logging()

# ============================================================
# OpenAI 설정
# ============================================================
OPENAI_API_KEY: str = ""

# ============================================================
# 사용자 DB (메모리)
# ============================================================
USERS: Dict[str, Dict[str, str]] = {
    "admin": {"password": "admin123", "role": "관리자", "name": "관리자"},
    "user": {"password": "user123", "role": "사용자", "name": "사용자"},
    "test": {"password": "test", "role": "사용자", "name": "테스트"},
}

# ============================================================
# 데이터프레임
# ============================================================
merchants: pd.DataFrame = pd.DataFrame()
metrics_clean: pd.DataFrame = pd.DataFrame()

# ============================================================
# 캐시
# ============================================================
LATEST_METRICS_MAP: Dict[str, pd.Series] = {}
METRICS_BY_MERCHANT: Dict[str, pd.DataFrame] = {}
INDUSTRY_NORM_MAP: Dict[str, str] = {}

# ============================================================
# ML 모델
# ============================================================
rf_reg: Optional[Any] = None
iso_forest: Optional[Any] = None
rf_clf: Optional[Any] = None
scaler: Optional[Any] = None
le_industry: Optional[Any] = None
le_region: Optional[Any] = None
le_growth: Optional[Any] = None

# ============================================================
# 추천 시스템
# ============================================================
sar_model: Optional[Any] = None
POPULAR_MERCHANTS: List[Dict[str, Any]] = []

# ============================================================
# 최근 컨텍스트 저장 (요약 재활용)
# ============================================================
LAST_CONTEXT_STORE: Dict[str, Dict[str, Any]] = {}
LAST_CONTEXT_LOCK = Lock()
LAST_CONTEXT_TTL_SEC = 600

# ============================================================
# RAG 설정/상태
# ============================================================
RAG_DOCS_DIR = os.path.join(BASE_DIR, "rag_docs")
RAG_FAISS_DIR = os.path.join(BASE_DIR, "rag_faiss")
RAG_STATE_FILE = os.path.join(RAG_FAISS_DIR, "rag_state.json")
RAG_EMBED_MODEL = "text-embedding-3-small"
RAG_ALLOWED_EXTS = {".txt", ".md", ".json", ".csv", ".log", ".pdf"}
RAG_MAX_DOC_CHARS = 200000
RAG_SNIPPET_CHARS = 1200
RAG_DEFAULT_TOPK = 3
RAG_MAX_TOPK = 10

RAG_LOCK = Lock()
RAG_STORE: Dict[str, Any] = {
    "ready": False,
    "hash": "",
    "docs_count": 0,
    "last_build_ts": 0.0,
    "error": "",
    "index": None,
}
