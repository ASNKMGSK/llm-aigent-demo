"""
rag/graph_rag.py - GraphRAG 구현 (LLM 기반 엔티티/관계 추출 + NetworkX 그래프)

Microsoft GraphRAG 아키텍처 참고:
1. LLM으로 엔티티/관계 추출
2. NetworkX로 지식 그래프 구축
3. 커뮤니티 탐지 (Louvain 알고리즘)
4. 그래프 기반 검색
"""
import json
import hashlib
from typing import List, Dict, Any, Tuple, Optional

from core.utils import safe_str
import state as st

# NetworkX (그래프 라이브러리)
try:
    import networkx as nx
    from networkx.algorithms import community as nx_community
    NETWORKX_AVAILABLE = True
except ImportError:
    nx = None
    nx_community = None
    NETWORKX_AVAILABLE = False

# OpenAI for LLM-based extraction
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


# ============================================================
# Global Graph State
# ============================================================
GRAPH_RAG_STORE: Dict[str, Any] = {
    "graph": None,           # NetworkX Graph
    "entities": {},          # entity_id -> entity_data
    "relations": [],         # list of relations
    "communities": {},       # community_id -> list of entity_ids
    "summaries": {},         # community_id -> summary text
    "ready": False,
    "doc_hash": "",
}


# ============================================================
# LLM-based Entity/Relation Extraction
# ============================================================
EXTRACTION_PROMPT = """다음 텍스트에서 엔티티(개체)와 관계를 추출해주세요.

텍스트:
{text}

다음 JSON 형식으로 응답해주세요:
{{
  "entities": [
    {{"id": "고유ID", "name": "엔티티명", "type": "유형(PERSON/ORG/TECH/CONCEPT/PRODUCT)", "description": "설명"}}
  ],
  "relations": [
    {{"source": "소스엔티티ID", "target": "타겟엔티티ID", "type": "관계유형", "description": "관계설명"}}
  ]
}}

규칙:
- 중요한 엔티티만 추출 (사람, 조직, 기술, 개념, 제품 등)
- 관계는 엔티티 간의 연결을 나타냄
- ID는 영문으로, 공백 없이
- JSON만 출력, 다른 텍스트 없이"""


def extract_entities_relations_llm(
    text: str,
    api_key: str,
    model: str = "gpt-4o-mini"
) -> Tuple[List[Dict], List[Dict]]:
    """LLM을 사용하여 텍스트에서 엔티티와 관계 추출"""
    if not OPENAI_AVAILABLE or not api_key:
        return [], []

    try:
        client = OpenAI(api_key=api_key)

        # 텍스트가 너무 길면 자르기
        max_chars = 4000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a knowledge extraction assistant. Extract entities and relations from text and return JSON only."},
                {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()

        # JSON 파싱 시도
        # ```json ... ``` 형식 처리
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        data = json.loads(content)
        entities = data.get("entities", [])
        relations = data.get("relations", [])

        return entities, relations

    except json.JSONDecodeError as e:
        st.logger.warning("GRAPHRAG_JSON_PARSE_FAIL err=%s", safe_str(e))
        return [], []
    except Exception as e:
        st.logger.warning("GRAPHRAG_EXTRACT_FAIL err=%s", safe_str(e))
        return [], []


# ============================================================
# Graph Construction
# ============================================================
def build_graph_from_chunks(
    chunks: List[Any],
    api_key: str,
    max_chunks: int = 20
) -> bool:
    """청크들에서 GraphRAG 지식 그래프 구축"""
    global GRAPH_RAG_STORE

    if not NETWORKX_AVAILABLE:
        st.logger.warning("GRAPHRAG_NETWORKX_NOT_AVAILABLE")
        return False

    if not api_key:
        st.logger.warning("GRAPHRAG_NO_API_KEY")
        return False

    try:
        # 새 그래프 생성
        G = nx.Graph()
        all_entities = {}
        all_relations = []

        # 청크 수 제한 (비용 절감)
        process_chunks = chunks[:max_chunks]
        st.logger.info("GRAPHRAG_BUILD_START chunks=%d (max=%d)", len(process_chunks), max_chunks)

        for i, chunk in enumerate(process_chunks):
            try:
                content = safe_str(getattr(chunk, "page_content", ""))
                source = getattr(chunk, "metadata", {}).get("source", f"chunk_{i}")

                if not content or len(content) < 50:
                    continue

                # LLM으로 엔티티/관계 추출
                entities, relations = extract_entities_relations_llm(content, api_key)

                # 엔티티 추가
                for ent in entities:
                    ent_id = ent.get("id", "")
                    if not ent_id:
                        continue

                    if ent_id not in all_entities:
                        all_entities[ent_id] = {
                            "name": ent.get("name", ent_id),
                            "type": ent.get("type", "UNKNOWN"),
                            "description": ent.get("description", ""),
                            "sources": [source],
                            "mention_count": 1,
                        }
                        G.add_node(ent_id, **all_entities[ent_id])
                    else:
                        all_entities[ent_id]["mention_count"] += 1
                        if source not in all_entities[ent_id]["sources"]:
                            all_entities[ent_id]["sources"].append(source)

                # 관계 추가
                for rel in relations:
                    src = rel.get("source", "")
                    tgt = rel.get("target", "")
                    if src and tgt and src in all_entities and tgt in all_entities:
                        rel_data = {
                            "type": rel.get("type", "RELATED"),
                            "description": rel.get("description", ""),
                        }
                        all_relations.append({**rel, "source_doc": source})
                        G.add_edge(src, tgt, **rel_data)

                st.logger.info("GRAPHRAG_CHUNK_PROCESSED %d/%d entities=%d relations=%d",
                              i + 1, len(process_chunks), len(entities), len(relations))

            except Exception as e:
                st.logger.warning("GRAPHRAG_CHUNK_FAIL chunk=%d err=%s", i, safe_str(e))
                continue

        if len(all_entities) == 0:
            st.logger.warning("GRAPHRAG_NO_ENTITIES")
            GRAPH_RAG_STORE["ready"] = False
            return False

        # 커뮤니티 탐지
        communities = detect_communities(G)

        # 상태 저장
        GRAPH_RAG_STORE.update({
            "graph": G,
            "entities": all_entities,
            "relations": all_relations,
            "communities": communities,
            "ready": True,
        })

        st.logger.info("GRAPHRAG_BUILD_DONE entities=%d relations=%d communities=%d",
                      len(all_entities), len(all_relations), len(communities))
        return True

    except Exception as e:
        st.logger.exception("GRAPHRAG_BUILD_FAIL err=%s", safe_str(e))
        GRAPH_RAG_STORE["ready"] = False
        return False


# ============================================================
# Community Detection
# ============================================================
def detect_communities(G: Any) -> Dict[int, List[str]]:
    """Louvain 알고리즘으로 커뮤니티 탐지"""
    if not NETWORKX_AVAILABLE or G is None or G.number_of_nodes() == 0:
        return {}

    try:
        # Louvain 커뮤니티 탐지 시도
        try:
            communities_gen = nx_community.louvain_communities(G, seed=42)
            communities = {i: list(c) for i, c in enumerate(communities_gen)}
        except Exception:
            # Fallback: connected components
            communities = {i: list(c) for i, c in enumerate(nx.connected_components(G))}

        st.logger.info("GRAPHRAG_COMMUNITIES_DETECTED count=%d", len(communities))
        return communities

    except Exception as e:
        st.logger.warning("GRAPHRAG_COMMUNITY_FAIL err=%s", safe_str(e))
        return {}


# ============================================================
# Graph-based Retrieval
# ============================================================
def search_graph_rag(
    query: str,
    api_key: str,
    top_k: int = 5,
    include_neighbors: bool = True
) -> Dict[str, Any]:
    """GraphRAG 검색 - 쿼리와 관련된 엔티티/관계/커뮤니티 검색"""
    global GRAPH_RAG_STORE

    if not GRAPH_RAG_STORE.get("ready"):
        return {"status": "FAILED", "error": "GraphRAG not ready", "results": []}

    G = GRAPH_RAG_STORE.get("graph")
    entities = GRAPH_RAG_STORE.get("entities", {})
    communities = GRAPH_RAG_STORE.get("communities", {})

    if G is None or len(entities) == 0:
        return {"status": "FAILED", "error": "Graph is empty", "results": []}

    try:
        # 1. 쿼리에서 관련 엔티티 찾기 (단순 매칭)
        query_lower = query.lower()
        matched_entities = []

        for ent_id, ent_data in entities.items():
            score = 0
            name = ent_data.get("name", "").lower()
            desc = ent_data.get("description", "").lower()

            # 이름 매칭
            if query_lower in name or name in query_lower:
                score += 10
            # 설명 매칭
            if query_lower in desc:
                score += 5
            # 단어 매칭
            for word in query_lower.split():
                if len(word) > 1:
                    if word in name:
                        score += 3
                    if word in desc:
                        score += 1

            if score > 0:
                matched_entities.append({
                    "id": ent_id,
                    "score": score,
                    **ent_data
                })

        # 점수로 정렬
        matched_entities.sort(key=lambda x: x["score"], reverse=True)
        matched_entities = matched_entities[:top_k]

        # 2. 이웃 엔티티 포함 (그래프 탐색)
        neighbor_entities = []
        if include_neighbors and G is not None:
            for ent in matched_entities[:3]:  # 상위 3개만
                ent_id = ent["id"]
                if G.has_node(ent_id):
                    for neighbor in G.neighbors(ent_id):
                        if neighbor not in [e["id"] for e in matched_entities]:
                            if neighbor in entities:
                                neighbor_entities.append({
                                    "id": neighbor,
                                    "score": ent["score"] * 0.5,
                                    "via": ent_id,
                                    **entities[neighbor]
                                })

        # 3. 관련 커뮤니티 찾기
        related_communities = []
        matched_ids = [e["id"] for e in matched_entities]
        for comm_id, members in communities.items():
            overlap = len(set(members) & set(matched_ids))
            if overlap > 0:
                related_communities.append({
                    "community_id": comm_id,
                    "member_count": len(members),
                    "matched_count": overlap,
                    "members": members[:10],  # 최대 10개만
                })

        # 4. 관련 관계 찾기
        related_relations = []
        all_relations = GRAPH_RAG_STORE.get("relations", [])
        for rel in all_relations:
            if rel.get("source") in matched_ids or rel.get("target") in matched_ids:
                related_relations.append(rel)

        return {
            "status": "SUCCESS",
            "query": query,
            "matched_entities": matched_entities,
            "neighbor_entities": neighbor_entities[:top_k],
            "related_communities": related_communities,
            "related_relations": related_relations[:10],
            "graph_stats": {
                "total_entities": len(entities),
                "total_relations": len(all_relations),
                "total_communities": len(communities),
            }
        }

    except Exception as e:
        st.logger.exception("GRAPHRAG_SEARCH_FAIL err=%s", safe_str(e))
        return {"status": "FAILED", "error": safe_str(e), "results": []}


# ============================================================
# Status & Utils
# ============================================================
def get_graph_rag_status() -> Dict[str, Any]:
    """GraphRAG 상태 반환"""
    global GRAPH_RAG_STORE

    G = GRAPH_RAG_STORE.get("graph")

    return {
        "ready": GRAPH_RAG_STORE.get("ready", False),
        "networkx_available": NETWORKX_AVAILABLE,
        "openai_available": OPENAI_AVAILABLE,
        "entity_count": len(GRAPH_RAG_STORE.get("entities", {})),
        "relation_count": len(GRAPH_RAG_STORE.get("relations", [])),
        "community_count": len(GRAPH_RAG_STORE.get("communities", {})),
        "node_count": G.number_of_nodes() if G else 0,
        "edge_count": G.number_of_edges() if G else 0,
    }


def clear_graph_rag():
    """GraphRAG 초기화"""
    global GRAPH_RAG_STORE
    GRAPH_RAG_STORE = {
        "graph": None,
        "entities": {},
        "relations": [],
        "communities": {},
        "summaries": {},
        "ready": False,
        "doc_hash": "",
    }
