"""
rag/service.py - RAG (Retrieval-Augmented Generation) 서비스
임베딩 인덱스 구축, 검색, 파일 관리

Advanced Features:
- Hybrid Search: BM25 + Vector (FAISS) 조합
- Reranking: Cross-Encoder 기반 재정렬
- Knowledge Graph: 간단한 Entity-Relation 추출
"""
import os
import re
import json
import time
import hashlib
import tempfile
import shutil
from typing import List, Any, Dict, Tuple, Optional

from core.utils import safe_str
import state as st

# ============================================================
# 선택적 import (없으면 RAG 비활성화)
# ============================================================
FAISS = None
OpenAIEmbeddings = None
Document = None
RecursiveCharacterTextSplitter = None

try:
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    pass

# SAR import (현재 파일에서는 사용하지 않지만 기존 코드 유지)
SARSingleNode = None
SAR_AVAILABLE = False
try:
    from recommenders.models.sar.sar_singlenode import SARSingleNode
    SAR_AVAILABLE = True
except Exception:
    pass

# ============================================================
# Hybrid Search: BM25 (Optional)
# ============================================================
BM25Okapi = None
BM25_AVAILABLE = False
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    pass

# ============================================================
# Reranking: Cross-Encoder (Optional)
# ============================================================
CrossEncoder = None
RERANKER_AVAILABLE = False
RERANKER_MODEL = None
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    pass

# ============================================================
# Knowledge Graph (Simple Entity-Relation Extraction)
# ============================================================
KNOWLEDGE_GRAPH: Dict[str, List[Dict]] = {}  # entity -> relations


# ============================================================
# 내부 유틸
# ============================================================
def _sha1_text(s: str) -> str:
    try:
        return hashlib.sha1((s or "").encode("utf-8", errors="ignore")).hexdigest()
    except Exception:
        return ""


def _clean_text_for_rag(txt: str) -> str:
    if not txt:
        return ""
    # 제어문자 제거 (개행/탭은 살림)
    txt = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", txt)
    # 공백 정리
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def _is_garbage_text(txt: str) -> bool:
    if not txt:
        return True
    t = txt.strip()
    if len(t) < 50:
        return True

    # 문자 다양도 너무 낮으면(깨진 PDF/목차/반복) 제거
    uniq = len(set(t))
    if uniq / max(1, len(t)) < 0.02:
        return True

    # 한글/영문/숫자 비율이 너무 낮으면(깨진 텍스트) 제거
    meaningful = re.findall(r"[가-힣A-Za-z0-9]", t)
    if len(meaningful) / max(1, len(t)) < 0.2:
        return True

    return False


def _rag_list_files() -> List[str]:
    files: List[str] = []
    try:
        os.makedirs(st.RAG_DOCS_DIR, exist_ok=True)
        for root, _, names in os.walk(st.RAG_DOCS_DIR):
            for n in names:
                ext = os.path.splitext(n)[1].lower()
                if ext in st.RAG_ALLOWED_EXTS:
                    files.append(os.path.join(root, n))
    except Exception:
        return []
    return sorted(list(set(files)))


def _rag_files_fingerprint(paths: List[str]) -> str:
    parts: List[str] = []
    for p in paths:
        try:
            s = os.stat(p)
            parts.append(f"{os.path.relpath(p, st.RAG_DOCS_DIR)}|{s.st_size}|{int(s.st_mtime)}")
        except Exception:
            parts.append(f"{os.path.relpath(p, st.RAG_DOCS_DIR)}|ERR")
    return _sha1_text("\n".join(parts))


def _extract_text_from_pdf(path: str) -> str:
    try:
        try:
            from pypdf import PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                return ""
        reader = PdfReader(path)
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts).strip()
    except Exception:
        return ""


def _rag_read_file(path: str) -> str:
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            txt = _extract_text_from_pdf(path)
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()

        txt = (txt or "").strip()
        if len(txt) > st.RAG_MAX_DOC_CHARS:
            txt = txt[:st.RAG_MAX_DOC_CHARS]

        txt = _clean_text_for_rag(txt)
        if _is_garbage_text(txt):
            return ""
        return txt
    except Exception:
        return ""


def _make_embeddings(api_key: str):
    if OpenAIEmbeddings is None:
        return None
    k = (api_key or "").strip()
    try:
        return OpenAIEmbeddings(model=st.RAG_EMBED_MODEL, openai_api_key=k)
    except TypeError:
        try:
            return OpenAIEmbeddings(model=st.RAG_EMBED_MODEL, api_key=k)
        except TypeError:
            try:
                return OpenAIEmbeddings(model=st.RAG_EMBED_MODEL)
            except Exception:
                return None
    except Exception:
        return None


def _rag_load_state_file() -> dict:
    try:
        if not os.path.exists(st.RAG_STATE_FILE):
            return {}
        with open(st.RAG_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _rag_save_state_file(payload: dict) -> None:
    try:
        os.makedirs(st.RAG_FAISS_DIR, exist_ok=True)
        with open(st.RAG_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ============================================================
# BM25 인덱스 관리
# ============================================================
BM25_INDEX: Optional[Any] = None
BM25_CORPUS: List[str] = []
BM25_DOC_MAP: List[Dict] = []  # BM25 corpus index -> document metadata


def _tokenize_korean(text: str) -> List[str]:
    """한국어/영어 토큰화 (간단한 whitespace + 한글 음절 분리)"""
    if not text:
        return []
    # 공백 기준 토큰화
    tokens = text.lower().split()
    # 추가: 한글 음절 단위로도 분리 (형태소 분석기 없이 단순화)
    result = []
    for tok in tokens:
        result.append(tok)
        # 한글이면 2글자 이상일 때 ngram 추가
        if re.search(r'[가-힣]', tok) and len(tok) >= 2:
            for i in range(len(tok) - 1):
                result.append(tok[i:i+2])
    return result


def _build_bm25_index(chunks: List[Any]) -> bool:
    """BM25 인덱스 빌드"""
    global BM25_INDEX, BM25_CORPUS, BM25_DOC_MAP

    if not BM25_AVAILABLE or BM25Okapi is None:
        return False

    try:
        BM25_CORPUS = []
        BM25_DOC_MAP = []

        for chunk in chunks:
            try:
                content = safe_str(getattr(chunk, "page_content", ""))
                metadata = getattr(chunk, "metadata", {})
                if content:
                    BM25_CORPUS.append(content)
                    BM25_DOC_MAP.append({
                        "content": content,
                        "source": metadata.get("source", ""),
                    })
            except Exception:
                continue

        if not BM25_CORPUS:
            return False

        # BM25 인덱스 생성
        tokenized_corpus = [_tokenize_korean(doc) for doc in BM25_CORPUS]
        BM25_INDEX = BM25Okapi(tokenized_corpus)
        st.logger.info("BM25_INDEX_BUILT docs=%d", len(BM25_CORPUS))
        return True
    except Exception as e:
        st.logger.warning("BM25_BUILD_FAIL err=%s", safe_str(e))
        return False


def _bm25_search(query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
    """BM25 검색 (키워드 기반)"""
    global BM25_INDEX, BM25_DOC_MAP

    if BM25_INDEX is None or not BM25_DOC_MAP:
        return []

    try:
        tokenized_query = _tokenize_korean(query)
        scores = BM25_INDEX.get_scores(tokenized_query)

        # 상위 top_k 결과
        scored_docs = list(zip(range(len(scores)), scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored_docs[:top_k]:
            if score > 0:
                results.append((BM25_DOC_MAP[idx], score))

        return results
    except Exception as e:
        st.logger.warning("BM25_SEARCH_FAIL err=%s", safe_str(e))
        return []


# ============================================================
# Cross-Encoder Reranking
# ============================================================
def _get_reranker():
    """Reranker 모델 로드 (Lazy Loading)"""
    global RERANKER_MODEL

    if not RERANKER_AVAILABLE or CrossEncoder is None:
        return None

    if RERANKER_MODEL is not None:
        return RERANKER_MODEL

    try:
        # 다국어 지원 cross-encoder 모델 사용
        RERANKER_MODEL = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512)
        st.logger.info("RERANKER_LOADED model=ms-marco-MiniLM-L-6-v2")
        return RERANKER_MODEL
    except Exception as e:
        st.logger.warning("RERANKER_LOAD_FAIL err=%s", safe_str(e))
        return None


def _rerank_results(query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
    """Cross-Encoder로 결과 재정렬"""
    reranker = _get_reranker()
    if reranker is None or not results:
        return results[:top_k]

    try:
        # query-document 쌍 생성
        pairs = [(query, r.get("content", "")[:500]) for r in results]

        # Cross-encoder 점수 계산
        scores = reranker.predict(pairs)

        # 점수로 정렬
        scored_results = list(zip(results, scores))
        scored_results.sort(key=lambda x: x[1], reverse=True)

        reranked = []
        for r, score in scored_results[:top_k]:
            r["rerank_score"] = round(float(score), 4)
            reranked.append(r)

        return reranked
    except Exception as e:
        st.logger.warning("RERANK_FAIL err=%s", safe_str(e))
        return results[:top_k]


# ============================================================
# Hybrid Search (BM25 + Vector Fusion)
# ============================================================
def _reciprocal_rank_fusion(
    bm25_results: List[Tuple[Dict, float]],
    vector_results: List[Tuple[Dict, float]],
    k: int = 60
) -> List[Dict]:
    """
    Reciprocal Rank Fusion (RRF) - BM25와 Vector 결과 병합
    RRF score = sum(1 / (k + rank))
    """
    fusion_scores: Dict[str, Dict] = {}

    # BM25 결과 처리
    for rank, (doc, score) in enumerate(bm25_results):
        key = doc.get("content", "")[:100]  # 내용 해시로 중복 방지
        if key not in fusion_scores:
            fusion_scores[key] = {
                "doc": doc,
                "bm25_score": score,
                "vector_score": 0.0,
                "rrf_score": 0.0,
            }
        fusion_scores[key]["bm25_score"] = score
        fusion_scores[key]["rrf_score"] += 1.0 / (k + rank + 1)

    # Vector 결과 처리 (score = distance, 낮을수록 좋음)
    for rank, (doc, dist) in enumerate(vector_results):
        key = doc.get("content", "")[:100]
        if key not in fusion_scores:
            fusion_scores[key] = {
                "doc": doc,
                "bm25_score": 0.0,
                "vector_score": 1.0 / (1.0 + dist),  # distance -> similarity
                "rrf_score": 0.0,
            }
        fusion_scores[key]["vector_score"] = 1.0 / (1.0 + dist)
        fusion_scores[key]["rrf_score"] += 1.0 / (k + rank + 1)

    # RRF 점수로 정렬
    sorted_results = sorted(
        fusion_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )

    return [
        {
            **item["doc"],
            "bm25_score": round(item["bm25_score"], 4),
            "vector_score": round(item["vector_score"], 4),
            "fusion_score": round(item["rrf_score"], 4),
        }
        for item in sorted_results
    ]


# ============================================================
# Knowledge Graph (Simple Entity-Relation Extraction)
# ============================================================
def _extract_entities_simple(text: str) -> List[str]:
    """간단한 개체명 추출 (정규식 기반)"""
    entities = []

    # 한글 고유명사 패턴 (2-10글자, 주로 명사형)
    korean_entities = re.findall(r'[가-힣]{2,10}(?:서비스|시스템|솔루션|플랫폼|회사|은행|카드)', text)
    entities.extend(korean_entities)

    # 영문 고유명사 (대문자로 시작하는 단어 연속)
    english_entities = re.findall(r'[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*', text)
    entities.extend([e for e in english_entities if len(e) > 2])

    # 기술 용어
    tech_terms = re.findall(r'(?:API|SDK|DB|AI|ML|LLM|RAG|OCR|NLP|GPU|CPU)\b', text.upper())
    entities.extend(tech_terms)

    return list(set(entities))


def _extract_relations_simple(text: str, entities: List[str]) -> List[Dict]:
    """간단한 관계 추출 (패턴 기반)"""
    relations = []

    # 관계 패턴
    relation_patterns = [
        (r'(\S+)(?:은|는|이|가)\s+(\S+)(?:을|를|와|과)\s+(사용|활용|연동|처리|분석)', 'uses'),
        (r'(\S+)(?:은|는|이|가)\s+(\S+)(?:의|에)\s+(일부|포함|속함)', 'part_of'),
        (r'(\S+)(?:은|는)\s+(\S+)(?:와|과)\s+(연결|연동|통합)', 'connected_to'),
    ]

    for pattern, rel_type in relation_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) >= 2:
                relations.append({
                    "source": match[0],
                    "target": match[1],
                    "type": rel_type,
                })

    return relations


def build_knowledge_graph(chunks: List[Any]) -> Dict:
    """청크에서 Knowledge Graph 구축"""
    global KNOWLEDGE_GRAPH

    KNOWLEDGE_GRAPH = {}
    entity_docs: Dict[str, List[str]] = {}  # entity -> document sources
    all_relations = []

    for chunk in chunks:
        try:
            content = safe_str(getattr(chunk, "page_content", ""))
            source = getattr(chunk, "metadata", {}).get("source", "unknown")

            # 개체 추출
            entities = _extract_entities_simple(content)
            for entity in entities:
                if entity not in entity_docs:
                    entity_docs[entity] = []
                if source not in entity_docs[entity]:
                    entity_docs[entity].append(source)

            # 관계 추출
            relations = _extract_relations_simple(content, entities)
            all_relations.extend(relations)
        except Exception:
            continue

    # Knowledge Graph 구조화
    KNOWLEDGE_GRAPH = {
        "entities": entity_docs,
        "relations": all_relations,
        "stats": {
            "entity_count": len(entity_docs),
            "relation_count": len(all_relations),
        }
    }

    st.logger.info("KNOWLEDGE_GRAPH_BUILT entities=%d relations=%d",
                   len(entity_docs), len(all_relations))
    return KNOWLEDGE_GRAPH


def search_knowledge_graph(query: str, top_k: int = 5) -> List[Dict]:
    """Knowledge Graph에서 관련 엔티티 검색"""
    global KNOWLEDGE_GRAPH

    if not KNOWLEDGE_GRAPH or "entities" not in KNOWLEDGE_GRAPH:
        return []

    results = []
    query_lower = query.lower()

    for entity, sources in KNOWLEDGE_GRAPH.get("entities", {}).items():
        entity_lower = entity.lower()
        score = 0

        # 정확히 일치
        if entity_lower in query_lower or query_lower in entity_lower:
            score = 10
        # 부분 일치
        elif any(word in entity_lower for word in query_lower.split()):
            score = 5

        if score > 0:
            # 관련 관계 찾기
            related_relations = [
                r for r in KNOWLEDGE_GRAPH.get("relations", [])
                if r.get("source") == entity or r.get("target") == entity
            ]

            results.append({
                "entity": entity,
                "sources": sources,
                "relations": related_relations[:3],
                "score": score,
            })

    # 점수로 정렬
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ============================================================
# FAISS 한글 경로 대응 (Windows C++ I/O 우회)
# ============================================================
def _safe_faiss_save(idx, target_dir: str) -> None:
    """FAISS 인덱스를 저장. 한글 경로면 임시 디렉토리 경유."""
    os.makedirs(target_dir, exist_ok=True)
    try:
        idx.save_local(target_dir)
        return
    except Exception:
        pass
    with tempfile.TemporaryDirectory() as tmp:
        idx.save_local(tmp)
        for fname in os.listdir(tmp):
            shutil.copy2(os.path.join(tmp, fname), os.path.join(target_dir, fname))


def _safe_faiss_load(target_dir: str, emb):
    """FAISS 인덱스를 로드. 한글 경로면 임시 디렉토리로 복사 후 로드."""
    try:
        try:
            return FAISS.load_local(target_dir, emb, allow_dangerous_deserialization=True)
        except TypeError:
            return FAISS.load_local(target_dir, emb)
    except Exception:
        pass
    with tempfile.TemporaryDirectory() as tmp:
        for fname in os.listdir(target_dir):
            src = os.path.join(target_dir, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(tmp, fname))
        try:
            return FAISS.load_local(tmp, emb, allow_dangerous_deserialization=True)
        except TypeError:
            return FAISS.load_local(tmp, emb)


# ============================================================
# 인덱스 빌드/로드
# ============================================================
def rag_build_or_load_index(api_key: str, force_rebuild: bool = False) -> None:
    with st.RAG_LOCK:
        st.RAG_STORE["error"] = ""

    if (FAISS is None) or (OpenAIEmbeddings is None) or (Document is None):
        with st.RAG_LOCK:
            st.RAG_STORE.update({
                "ready": False, "index": None,
                "error": "RAG 비활성화: langchain_community/FAISS 또는 OpenAIEmbeddings 또는 Document import 실패",
            })
        return

    k = (api_key or "").strip()
    if not k:
        with st.RAG_LOCK:
            st.RAG_STORE.update({
                "ready": False, "index": None,
                "error": "RAG 비활성화: OpenAI API Key가 없습니다.(환경변수 OPENAI_API_KEY 또는 요청 apiKey 필요)",
            })
        return

    paths = _rag_list_files()
    fp = _rag_files_fingerprint(paths)

    # 기존 인덱스 로드 (파일 해시 동일)
    if (not force_rebuild) and os.path.exists(st.RAG_FAISS_DIR):
        saved = _rag_load_state_file()
        if isinstance(saved, dict) and saved.get("hash") == fp:
            try:
                emb = _make_embeddings(k)
                if emb is None:
                    raise RuntimeError("embeddings_init_failed")
                idx = _safe_faiss_load(st.RAG_FAISS_DIR, emb)
                with st.RAG_LOCK:
                    st.RAG_STORE.update({
                        "ready": True, "hash": fp,
                        "files_count": int(saved.get("files_count") or saved.get("docs_count") or 0),
                        "chunks_count": int(saved.get("chunks_count") or saved.get("docs_count") or 0),
                        "last_build_ts": float(saved.get("last_build_ts") or time.time()),
                        "error": "", "index": idx,
                    })
                st.logger.info("RAG_READY(load) files=%s chunks=%s hash=%s",
                              st.RAG_STORE.get("files_count"), st.RAG_STORE.get("chunks_count"), safe_str(fp)[:10])
                return
            except Exception as e:
                st.logger.warning("RAG_LOAD_FAIL err=%s", safe_str(e))

    # 새로 빌드
    docs: List[Any] = []
    for p in paths:
        txt = _rag_read_file(p)
        if not txt:
            continue
        rel = os.path.relpath(p, st.RAG_DOCS_DIR).replace("\\", "/")
        try:
            docs.append(Document(page_content=txt, metadata={"source": rel}))
        except Exception:
            continue

    if not docs:
        with st.RAG_LOCK:
            st.RAG_STORE.update({
                "ready": False, "index": None, "hash": fp,
                "files_count": 0, "chunks_count": 0,
                "last_build_ts": time.time(),
                "error": "rag_docs 폴더에 인덱싱할 문서가 없습니다.",
            })
        _rag_save_state_file({
            "hash": fp, "files_count": 0, "chunks_count": 0,
            "last_build_ts": float(st.RAG_STORE.get("last_build_ts") or time.time()),
            "error": safe_str(st.RAG_STORE.get("error", "")),
            "embed_model": st.RAG_EMBED_MODEL,
        })
        st.logger.info("RAG_EMPTY docs_dir=%s", st.RAG_DOCS_DIR)
        return

    # 청킹
    files_count = len(docs)  # 원본 문서 수
    chunks: List[Any] = []
    if RecursiveCharacterTextSplitter is not None:
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
            chunks = splitter.split_documents(docs)
        except Exception:
            chunks = docs
    else:
        chunks = docs
    chunks_count = len(chunks)  # 청크 수

    try:
        emb = _make_embeddings(k)
        if emb is None:
            raise RuntimeError("embeddings_init_failed")

        idx = FAISS.from_documents(chunks, emb)
        _safe_faiss_save(idx, st.RAG_FAISS_DIR)

        # BM25 인덱스 빌드 (Hybrid Search용)
        bm25_built = _build_bm25_index(chunks)

        # Knowledge Graph 빌드
        kg_built = False
        try:
            build_knowledge_graph(chunks)
            kg_built = True
        except Exception as e:
            st.logger.warning("KNOWLEDGE_GRAPH_BUILD_FAIL err=%s", safe_str(e))

        with st.RAG_LOCK:
            st.RAG_STORE.update({
                "ready": True, "hash": fp,
                "files_count": files_count,
                "chunks_count": chunks_count,
                "last_build_ts": time.time(),
                "error": "", "index": idx,
                "bm25_ready": bm25_built,
                "kg_ready": kg_built,
            })

        _rag_save_state_file({
            "hash": fp, "files_count": files_count, "chunks_count": chunks_count,
            "last_build_ts": float(st.RAG_STORE.get("last_build_ts") or time.time()),
            "error": "", "embed_model": st.RAG_EMBED_MODEL,
            "bm25_ready": bm25_built, "kg_ready": kg_built,
        })
        st.logger.info("RAG_READY(build) files=%s chunks=%s bm25=%s kg=%s hash=%s",
                       files_count, chunks_count, bm25_built, kg_built, safe_str(fp)[:10])
    except Exception as e:
        with st.RAG_LOCK:
            st.RAG_STORE.update({
                "ready": False, "index": None, "hash": fp,
                "files_count": 0, "chunks_count": 0,
                "error": f"RAG 인덱싱 실패: {safe_str(e)}",
            })
        st.logger.exception("RAG_BUILD_FAIL err=%s", safe_str(e))


# ============================================================
# FAISS 벡터 검색 (기본)
# ============================================================
def rag_search_local(query: str, top_k: int = st.RAG_DEFAULT_TOPK, api_key: str = "") -> List[dict]:
    q = safe_str(query).strip()
    if not q:
        return []

    k = max(1, min(int(top_k), st.RAG_MAX_TOPK))

    with st.RAG_LOCK:
        ready = bool(st.RAG_STORE.get("ready"))
        idx = st.RAG_STORE.get("index")
        err = safe_str(st.RAG_STORE.get("error", ""))

    if (not ready) or (idx is None):
        rag_build_or_load_index(api_key=api_key, force_rebuild=False)
        with st.RAG_LOCK:
            ready = bool(st.RAG_STORE.get("ready"))
            idx = st.RAG_STORE.get("index")
            err = safe_str(st.RAG_STORE.get("error", ""))
        if (not ready) or (idx is None):
            return [{"title": "RAG_ERROR", "source": "", "score": 0.0, "content": err}] if err else []

    try:
        pairs = idx.similarity_search_with_score(q, k=k)

        max_dist = float(getattr(st, "RAG_MAX_DISTANCE", 1.6))

        out: List[dict] = []
        for doc, score in pairs:
            if score is None:
                continue
            try:
                dist = float(score)
            except Exception:
                continue
            if dist > max_dist:
                continue

            src = ""
            try:
                src = safe_str(getattr(doc, "metadata", {}).get("source", ""))
            except Exception:
                src = ""
            try:
                txt = safe_str(getattr(doc, "page_content", ""))
            except Exception:
                txt = ""
            if not txt:
                continue

            out.append({
                "title": src or "doc",
                "source": src,
                "score": round(dist, 6),
                "content": txt[:st.RAG_SNIPPET_CHARS],
            })
        return out
    except Exception as e:
        return [{"title": "RAG_ERROR", "source": "", "score": 0.0, "content": f"RAG 검색 실패: {safe_str(e)}"}]


# ============================================================
# Hybrid Search (BM25 + Vector + Reranking)
# ============================================================
def rag_search_hybrid(
    query: str,
    top_k: int = st.RAG_DEFAULT_TOPK,
    api_key: str = "",
    use_reranking: bool = True,
    use_kg: bool = False
) -> dict:
    """
    고급 RAG 검색:
    - Hybrid Search: BM25 (키워드) + Vector (의미) 조합
    - Reranking: Cross-Encoder로 결과 재정렬
    - Knowledge Graph: 관련 엔티티/관계 포함 (선택)
    """
    q = safe_str(query).strip()
    if not q:
        return {"status": "FAILED", "error": "Empty query", "results": []}

    k = max(1, min(int(top_k), st.RAG_MAX_TOPK))
    effective_key = safe_str(api_key).strip() or st.OPENAI_API_KEY

    # 1. Vector Search (FAISS)
    vector_results = []
    with st.RAG_LOCK:
        ready = bool(st.RAG_STORE.get("ready"))
        idx = st.RAG_STORE.get("index")

    if (not ready) or (idx is None):
        rag_build_or_load_index(api_key=effective_key, force_rebuild=False)
        with st.RAG_LOCK:
            ready = bool(st.RAG_STORE.get("ready"))
            idx = st.RAG_STORE.get("index")

    if ready and idx is not None:
        try:
            pairs = idx.similarity_search_with_score(q, k=k * 2)  # 더 많이 가져와서 fusion
            for doc, dist in pairs:
                try:
                    content = safe_str(getattr(doc, "page_content", ""))
                    source = safe_str(getattr(doc, "metadata", {}).get("source", ""))
                    if content:
                        vector_results.append((
                            {"content": content, "source": source, "title": source or "doc"},
                            float(dist)
                        ))
                except Exception:
                    continue
        except Exception as e:
            st.logger.warning("HYBRID_VECTOR_FAIL err=%s", safe_str(e))

    # 2. BM25 Search (키워드 기반)
    bm25_results = []
    with st.RAG_LOCK:
        bm25_ready = bool(st.RAG_STORE.get("bm25_ready"))

    if bm25_ready and BM25_INDEX is not None:
        bm25_results = _bm25_search(q, top_k=k * 2)

    # 3. Reciprocal Rank Fusion
    if bm25_results and vector_results:
        fused_results = _reciprocal_rank_fusion(bm25_results, vector_results)
        search_method = "hybrid"
    elif vector_results:
        fused_results = [
            {**doc, "vector_score": round(1.0 / (1.0 + dist), 4), "fusion_score": round(1.0 / (1.0 + dist), 4)}
            for doc, dist in vector_results
        ]
        search_method = "vector"
    elif bm25_results:
        fused_results = [
            {**doc, "bm25_score": round(score, 4), "fusion_score": round(score / 100.0, 4)}
            for doc, score in bm25_results
        ]
        search_method = "bm25"
    else:
        return {"status": "FAILED", "error": "No search results", "results": []}

    # 4. Reranking (Cross-Encoder)
    reranked = False
    if use_reranking and RERANKER_AVAILABLE and len(fused_results) > 1:
        fused_results = _rerank_results(q, fused_results, top_k=k)
        reranked = True

    # top_k 제한 및 content 자르기
    final_results = []
    for r in fused_results[:k]:
        r["content"] = r.get("content", "")[:st.RAG_SNIPPET_CHARS]
        final_results.append(r)

    # 5. Knowledge Graph 보강 (선택)
    kg_entities = []
    if use_kg:
        with st.RAG_LOCK:
            kg_ready = bool(st.RAG_STORE.get("kg_ready"))
        if kg_ready:
            kg_entities = search_knowledge_graph(q, top_k=3)

    return {
        "status": "SUCCESS",
        "query": q,
        "top_k": k,
        "search_method": search_method,
        "reranked": reranked,
        "bm25_available": BM25_AVAILABLE and BM25_INDEX is not None,
        "reranker_available": RERANKER_AVAILABLE,
        "kg_available": bool(KNOWLEDGE_GRAPH),
        "results": final_results,
        "kg_entities": kg_entities,
    }


# ============================================================
# 글로서리(사전) 검색
# ============================================================
def rag_search_glossary(query: str, top_k: int = 3) -> List[dict]:
    from core.constants import RAG_DOCUMENTS
    query_lower = (query or "").lower()
    scores = []

    for _, doc in RAG_DOCUMENTS.items():
        score = 0
        for kw in doc.get("keywords", []):
            kw_lower = (kw or "").lower().strip()
            if kw_lower and kw_lower in query_lower:
                score += 2
        title_lower = (doc.get("title") or "").lower().strip()
        if title_lower and title_lower in query_lower:
            score += 3  # 제목 매칭은 더 크게
        scores.append((score, doc))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [
        {"title": doc["title"], "content": doc["content"], "source": "glossary", "score": float(sc)}
        for sc, doc in scores[:top_k]
        if sc > 0
    ]


# ============================================================
# 통합 RAG 검색 (FAISS + 글로서리)
# ============================================================
def tool_rag_search(query: str, top_k: int = st.RAG_DEFAULT_TOPK, api_key: str = "") -> dict:
    effective_key = safe_str(api_key).strip() or st.OPENAI_API_KEY
    k = int(max(1, min(int(top_k), st.RAG_MAX_TOPK)))

    gloss = rag_search_glossary(query, top_k=k)
    local = rag_search_local(query, top_k=k, api_key=effective_key)

    merged: List[dict] = []
    seen = set()

    # 1) glossary 먼저
    if isinstance(gloss, list):
        for r in gloss:
            key = safe_str(r.get("title") or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                merged.append({
                    "title": r.get("title"),
                    "source": "glossary",
                    "score": 0.0,
                    "priority": 1000.0 + float(r.get("score") or 0.0),
                    "content": safe_str(r.get("content") or "")[:st.RAG_SNIPPET_CHARS],
                })

    # 2) 로컬은 남은 슬롯만 채움
    remain = max(0, k - len(merged))
    if remain > 0 and isinstance(local, list):
        for r in local:
            key = safe_str(r.get("source") or r.get("title") or "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                dist = float(r.get("score") or 0.0)
                merged.append({
                    "title": r.get("title"),
                    "source": r.get("source"),
                    "score": round(dist, 6),
                    "priority": 100.0 / (1.0 + dist),
                    "content": safe_str(r.get("content") or "")[:st.RAG_SNIPPET_CHARS],
                })
                remain -= 1
                if remain <= 0:
                    break

    # 3) priority로 정렬
    merged.sort(key=lambda x: float(x.get("priority") or 0.0), reverse=True)
    for m in merged:
        m.pop("priority", None)

    with st.RAG_LOCK:
        rag_ready = bool(st.RAG_STORE.get("ready"))
        rag_err = safe_str(st.RAG_STORE.get("error", ""))
        rag_docs = int(st.RAG_STORE.get("docs_count") or 0)

    return {
        "status": "SUCCESS" if merged else "FAILED",
        "query": safe_str(query),
        "top_k": k,
        "rag_ready": rag_ready,
        "rag_docs_count": rag_docs,
        "rag_error": rag_err,
        "results": merged,
    }
