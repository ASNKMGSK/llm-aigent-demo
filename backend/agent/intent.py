"""
agent/intent.py - 인텐트 감지 및 결정적 도구 실행 라우팅
사용자 입력을 분석하여 적절한 도구를 실행합니다.
"""
import time
from typing import Optional, Dict, Any, Tuple

from core.constants import (
    RAG_DOCUMENTS, SUMMARY_TRIGGERS, DEFAULT_TOPN,
)
from core.utils import safe_str
from core.parsers import (
    extract_top_k_from_text, parse_month_range_from_text,
    extract_merchant_id, extract_customer_id, extract_industry_from_text,
)
from agent.tools import (
    tool_get_merchant_metrics, tool_get_merchant_metrics_history_summary,
    tool_predict_revenue, tool_detect_anomaly, tool_classify_growth,
    tool_rank_dimension, tool_rank_merchants, tool_compare_industry,
    tool_list_merchants, tool_recommend_merchants_for_customer,
    tool_recommend_similar_merchants, build_checklist_from_metrics,
    _latest_row_for_merchant,
)
from rag.service import tool_rag_search
import state as st


# ============================================================
# 요약 트리거 / 컨텍스트 재활용
# ============================================================
def _has_summary_trigger(user_text: str) -> bool:
    t = (user_text or "").lower()
    return any(k.lower() in t for k in SUMMARY_TRIGGERS)


def set_last_context(username: str, merchant_id: Optional[str], results: Dict[str, Any], user_text: str, mode: str) -> None:
    if not username:
        return
    if not isinstance(results, dict) or len(results) == 0:
        return
    with st.LAST_CONTEXT_LOCK:
        st.LAST_CONTEXT_STORE[username] = {
            "merchant_id": safe_str(merchant_id).strip().upper() if merchant_id else "",
            "results": results,
            "user_text": safe_str(user_text),
            "ts": time.time(),
            "mode": safe_str(mode),
        }


def get_last_context(username: str) -> Optional[Dict[str, Any]]:
    if not username:
        return None
    with st.LAST_CONTEXT_LOCK:
        return st.LAST_CONTEXT_STORE.get(username)


def can_reuse_last_context(username: str, merchant_id: Optional[str], user_text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    if not _has_summary_trigger(user_text):
        return (False, None)

    ctx = get_last_context(username)
    if not ctx or not isinstance(ctx.get("results"), dict) or len(ctx["results"]) == 0:
        return (False, None)

    ts = float(ctx.get("ts") or 0.0)
    if ts > 0 and (time.time() - ts) > st.LAST_CONTEXT_TTL_SEC:
        return (False, None)

    req_mid = safe_str(merchant_id).strip().upper() if merchant_id else ""
    last_mid = safe_str(ctx.get("merchant_id")).strip().upper()

    if req_mid:
        if req_mid == last_mid:
            return (True, ctx)
        return (False, None)

    r = ctx.get("results") or {}
    merchant_keys = (
        "get_merchant_metrics", "get_merchant_metrics_history_summary",
        "predict_revenue", "detect_anomaly", "classify_growth",
    )
    if last_mid and any(isinstance(r.get(k), dict) for k in merchant_keys):
        return (True, ctx)

    if isinstance(r.get("list_merchants"), dict) and r["list_merchants"].get("status") == "SUCCESS":
        return (True, ctx)

    for k in ("rank_merchants", "rank_industry", "rank_region", "rank_growth_type", "compare_industry", "rag_search"):
        if isinstance(r.get(k), dict) and r[k].get("status") in ("SUCCESS", "FAILED"):
            return (True, ctx)

    return (False, None)


# ============================================================
# 인텐트 감지
# ============================================================
def detect_intent(user_text: str) -> Dict[str, bool]:
    t = (user_text or "").strip().lower()

    rag_triggers = ["뜻", "용어", "설명", "정의", "개념", "meaning", "definition"]

    has_doc_keyword = False
    for _, doc in RAG_DOCUMENTS.items():
        for kw in doc.get("keywords", []):
            kw2 = (kw or "").strip().lower()
            if kw2 and (kw2 in t):
                has_doc_keyword = True
                break
        if has_doc_keyword:
            break

    status_triggers = ["현황", "현황분석", "현황 분석", "분석 시작", "대시보드", "dashboard"]
    force_full_status = any(x in t for x in status_triggers)

    simple_check_triggers = ["알아?", "알아", "뭐야?", "뭐야", "뭐지?", "뭐지", "누구", "누구야", "무엇", "what"]
    is_simple_check = any(t.endswith(x) or t.startswith(x) for x in simple_check_triggers)

    detailed_triggers = ["분석", "예측", "추천", "탐지", "추이", "비교", "랭킹", "리포트", "보고서"]
    is_detailed_request = any(x in t for x in detailed_triggers)

    want_simple_check = is_simple_check and not is_detailed_request

    industry_hit = False
    if st.INDUSTRY_NORM_MAP:
        vals = list(set(st.INDUSTRY_NORM_MAP.values()))
        for v in vals:
            if v and (v in (user_text or "")):
                industry_hit = True
                break

    rank_triggers = ["랭킹", "top", "상위", "순위", "베스트", "1등", "topn"]
    reco_triggers = ["추천", "recommend", "reco", "유사", "비슷한", "similar"]

    return {
        "want_simple_check": want_simple_check,
        "want_list": ("전체" in t and "가맹점" in t) or ("목록" in t) or ("리스트" in t),
        "want_rag": any(x in t for x in rag_triggers) or has_doc_keyword,
        "want_industry": industry_hit or (
            ("업종" in t) and (("비교" in t) or ("평균" in t) or ("대비" in t) or ("분석" in t) or ("리포트" in t) or ("보고서" in t) or ("조회" in t))
        ),
        "want_rank": any(x in t for x in rank_triggers),
        "want_revenue": ("매출" in t and "예측" in t) or ("예측" in t),
        "want_anomaly": ("이상" in t) or ("이상탐지" in t),
        "want_growth": ("성장" in t) or ("분류" in t),
        "want_history": ("추이" in t) or ("최근" in t) or ("개월" in t) or ("히스토리" in t),
        "want_metrics": ("지표" in t) or ("현황" in t) or ("조회" in t),
        "want_reco": any(x in t for x in reco_triggers),
        "want_reco_similar": ("유사" in t) or ("비슷한" in t) or ("similar" in t),
        "force_full_status": force_full_status,
    }


# ============================================================
# 결정적 도구 실행 파이프라인
# ============================================================
def run_deterministic_tools(user_text: str, merchant_id: Optional[str]) -> Dict[str, Any]:
    intents = detect_intent(user_text)
    results: Dict[str, Any] = {}

    # RAG는 용어/개념 질문일 때만 실행
    if intents.get("want_rag") and not intents.get("want_rank"):
        k = extract_top_k_from_text(user_text, default_k=st.RAG_DEFAULT_TOPK)
        results["rag_search"] = tool_rag_search(user_text, top_k=max(1, min(int(k), st.RAG_MAX_TOPK)), api_key="")

    sm, em = parse_month_range_from_text(user_text)

    # 간단한 확인 질문
    if intents.get("want_simple_check"):
        if merchant_id:
            results["get_merchant_metrics"] = tool_get_merchant_metrics(merchant_id)
            return results
        return results

    # 추천 요청
    if intents.get("want_reco"):
        cid = extract_customer_id(user_text)
        mid = extract_merchant_id(user_text)
        k = extract_top_k_from_text(user_text, default_k=DEFAULT_TOPN)

        if cid:
            results["recommend_merchants_for_customer"] = tool_recommend_merchants_for_customer(cid, top_k=k)
            return results

        if mid:
            results["recommend_similar_merchants"] = tool_recommend_similar_merchants(mid, top_k=k)
            return results

        results["recommend"] = {
            "status": "FAILED",
            "error": (
                "추천 요청에서 customer_id 또는 merchant_id를 찾지 못했습니다.\n"
                "예시:\n"
                "- 'C00055에게 추천할 가맹점 Top 10'\n"
                "- 'M0001과 유사한 가맹점 Top 10'\n"
                "- 'customer_id=C00055 top_k=10 추천'\n"
                "- 'merchant_id=M0001 top_k=10 유사'\n"
            ),
            "debug": {"parsed_customer_id": cid, "parsed_merchant_id": mid, "parsed_top_k": k},
        }
        return results

    # 랭킹 요청
    if intents.get("want_rank") and not merchant_id:
        top_n = extract_top_k_from_text(user_text, default_k=DEFAULT_TOPN)

        # 정렬 기준 결정
        metric = "total_revenue"
        if "성장" in (user_text or ""):
            metric = "revenue_growth_rate"
        if "재구매" in (user_text or ""):
            metric = "repeat_purchase_rate"

        # 특정 업종 추출 (예: "음식점 업종 Top 10" → industry="음식점")
        industry = extract_industry_from_text(user_text, st.INDUSTRY_NORM_MAP)

        # 특정 지역 추출 (예: "서울 지역 매출 상위 5개" → region="서울")
        region = None
        region_list = ["서울", "부산", "대구", "인천", "경기", "광주", "대전", "울산", "세종", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        for r in region_list:
            if r in (user_text or ""):
                region = r
                break

        # 특정 업종이나 지역이 있으면 rank_merchants로 필터링
        if industry or region:
            results["rank_merchants"] = tool_rank_merchants(metric, sm, em, top_n=top_n, industry=industry, region=region)
            return results

        # "업종별", "지역별" 집계 비교 요청인 경우 rank_dimension
        if ("업종별" in (user_text or "")) or ("업종 비교" in (user_text or "")):
            results["rank_industry"] = tool_rank_dimension("industry", sm, em, top_n=top_n)
            return results
        if ("지역별" in (user_text or "")) or ("지역 비교" in (user_text or "")):
            results["rank_region"] = tool_rank_dimension("region", sm, em, top_n=top_n)
            return results
        if ("성장유형별" in (user_text or "")) or ("성장 유형별" in (user_text or "")):
            results["rank_growth_type"] = tool_rank_dimension("growth_type", sm, em, top_n=top_n)
            return results

        # 기본: 전체 가맹점 랭킹
        results["rank_merchants"] = tool_rank_merchants(metric, sm, em, top_n=top_n)
        return results

    # 전체 목록
    if intents["want_list"] and not merchant_id:
        results["list_merchants"] = tool_list_merchants()
        return results

    # 업종 비교
    if intents["want_industry"] and not merchant_id:
        industry = extract_industry_from_text(user_text, st.INDUSTRY_NORM_MAP)
        if not industry and st.INDUSTRY_NORM_MAP:
            vals = list(set(st.INDUSTRY_NORM_MAP.values()))
            best = max((v for v in vals if v and (v in (user_text or ""))), key=len, default="")
            industry = best

        if not industry:
            results["compare_industry"] = {"status": "FAILED", "error": "업종명을 추출하지 못했습니다."}
            return results

        results["compare_industry"] = tool_compare_industry(industry)
        return results

    if not merchant_id:
        return results

    # 가맹점별 분석
    results["get_merchant_metrics"] = tool_get_merchant_metrics(merchant_id)

    if intents.get("force_full_status") and intents.get("want_metrics"):
        intents["want_history"] = True
        intents["want_revenue"] = True
        intents["want_anomaly"] = True
        intents["want_growth"] = True

    if intents["want_history"]:
        results["get_merchant_metrics_history_summary"] = tool_get_merchant_metrics_history_summary(merchant_id, months=6)

    if intents["want_revenue"]:
        results["predict_revenue"] = tool_predict_revenue(merchant_id, top_k=5, include_explain=True)

    if intents["want_anomaly"]:
        results["detect_anomaly"] = tool_detect_anomaly(merchant_id, top_k=5, include_explain=True)

    if intents["want_growth"]:
        results["classify_growth"] = tool_classify_growth(merchant_id, top_k=5, include_explain=True)

    latest = _latest_row_for_merchant(merchant_id)
    results["checklist"] = {"status": "SUCCESS", "items": build_checklist_from_metrics(latest)}

    return results
