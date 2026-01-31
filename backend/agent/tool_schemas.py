"""
agent/tool_schemas.py - LLM Tool Calling을 위한 도구 정의
LangChain @tool 데코레이터를 사용하여 LLM이 호출할 수 있는 도구들을 정의합니다.
"""
from typing import Optional
from langchain_core.tools import tool

from agent.tools import (
    tool_get_merchant_metrics,
    tool_get_merchant_metrics_history_summary,
    tool_predict_revenue,
    tool_detect_anomaly,
    tool_classify_growth,
    tool_list_merchants,
    tool_rank_merchants,
    tool_rank_dimension,
    tool_compare_industry,
    tool_recommend_merchants_for_customer,
    tool_recommend_similar_merchants,
)
from rag.service import tool_rag_search
import state as st


@tool
def get_merchant_metrics(merchant_id: str) -> dict:
    """
    특정 가맹점의 현재 현황(매출, 성장률, 객단가, 재구매율 등)을 조회합니다.

    Args:
        merchant_id: 가맹점 ID (예: M0001, M0002)

    Returns:
        가맹점의 현재 지표 정보
    """
    return tool_get_merchant_metrics(merchant_id)


@tool
def get_merchant_history(merchant_id: str, recent_n: int = 6) -> dict:
    """
    특정 가맹점의 최근 N개월 이력/추이를 조회합니다.

    Args:
        merchant_id: 가맹점 ID (예: M0001)
        recent_n: 조회할 최근 개월 수 (기본값: 6)

    Returns:
        가맹점의 월별 지표 이력
    """
    return tool_get_merchant_metrics_history_summary(merchant_id, recent_n)


@tool
def predict_revenue(merchant_id: str) -> dict:
    """
    특정 가맹점의 다음 달 매출을 예측합니다.
    RandomForest 모델 기반으로 예측하고 주요 영향 요인(feature importance)을 분석합니다.

    Args:
        merchant_id: 가맹점 ID (예: M0001)

    Returns:
        예측 매출, 변화율, 주요 영향 요인
    """
    return tool_predict_revenue(merchant_id)


@tool
def detect_anomaly(merchant_id: str) -> dict:
    """
    특정 가맹점의 이상 거래 패턴을 탐지합니다.
    Isolation Forest 모델 기반으로 정상/이상 여부를 판단합니다.

    Args:
        merchant_id: 가맹점 ID (예: M0001)

    Returns:
        이상 여부, 이상 점수, 주요 영향 요인
    """
    return tool_detect_anomaly(merchant_id)


@tool
def classify_growth(merchant_id: str) -> dict:
    """
    특정 가맹점의 성장 유형을 분류합니다.
    급성장/안정/정체/하락 중 하나로 분류하고 신뢰도를 제공합니다.

    Args:
        merchant_id: 가맹점 ID (예: M0001)

    Returns:
        성장 유형, 신뢰도, 주요 영향 요인
    """
    return tool_classify_growth(merchant_id)


@tool
def list_merchants(summary_only: bool = True) -> dict:
    """
    전체 가맹점 목록 또는 요약 통계를 조회합니다.

    Args:
        summary_only: True면 요약(업종별/지역별/성장유형별 집계)만, False면 전체 목록도 포함

    Returns:
        가맹점 수, 업종별/지역별/성장유형별 집계, (선택적) 전체 목록
    """
    return tool_list_merchants(summary_only)


@tool
def rank_merchants(
    metric: str = "total_revenue",
    top_n: int = 10,
    industry: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """
    개별 가맹점들의 순위 리스트를 조회합니다. 특정 업종이나 지역의 가맹점 Top N을 볼 때 사용합니다.

    사용 예시:
    - "음식점 업종 Top 10 가맹점" → industry="음식점", top_n=10
    - "서울 지역 매출 상위 5개" → region="서울", top_n=5
    - "카페 업종 성장률 Top 5" → industry="카페", metric="revenue_growth_rate", top_n=5

    Args:
        metric: 정렬 기준 (total_revenue=매출, revenue_growth_rate=성장률, repeat_purchase_rate=재구매율)
        top_n: 상위 몇 개를 조회할지 (기본값: 10, 최대: 50)
        industry: 업종 필터 (예: 음식점, IT서비스, 카페, 뷰티, 교육, 피트니스, 배달, 의류)
        region: 지역 필터 (예: 서울, 부산, 대구, 인천, 경기)

    Returns:
        개별 가맹점 ID, 이름, 매출 등 상세 정보가 포함된 순위 리스트
    """
    return tool_rank_merchants(metric, None, None, top_n, industry, region)


@tool
def rank_by_dimension(dimension: str, top_n: int = 10) -> dict:
    """
    업종별/지역별/성장유형별 집계 통계(평균 매출, 평균 성장률 등)를 조회합니다.
    개별 가맹점 리스트가 아닌, 그룹별 요약 통계를 볼 때 사용합니다.

    사용 예시:
    - "업종별 평균 매출 비교" → dimension="industry"
    - "지역별 성장률 통계" → dimension="region"
    - "성장유형별 분포" → dimension="growth_type"

    Args:
        dimension: 집계 기준 (industry=업종, region=지역, growth_type=성장유형)
        top_n: 상위 몇 개를 조회할지 (기본값: 10)

    Returns:
        그룹별 평균 매출, 평균 성장률, 가맹점 수 등 집계 통계
    """
    return tool_rank_dimension(dimension, None, None, top_n)


@tool
def compare_industry(industry: str) -> dict:
    """
    특정 업종의 평균 지표를 전체 평균과 비교 분석합니다.

    Args:
        industry: 업종명 (예: 음식점, IT서비스, 카페, 뷰티, 교육, 피트니스, 배달, 의류)

    Returns:
        업종 평균 vs 전체 평균 비교
    """
    return tool_compare_industry(industry)


@tool
def recommend_for_customer(customer_id: str, top_k: int = 10) -> dict:
    """
    특정 고객에게 추천할 가맹점을 조회합니다.
    SAR(Simple Algorithm for Recommendation) 모델 기반입니다.

    Args:
        customer_id: 고객 ID (예: C00001, C00055)
        top_k: 추천 개수 (기본값: 10)

    Returns:
        추천 가맹점 목록과 점수
    """
    return tool_recommend_merchants_for_customer(customer_id, top_k)


@tool
def recommend_similar_merchants(merchant_id: str, top_k: int = 10) -> dict:
    """
    특정 가맹점과 유사한 가맹점을 조회합니다.

    Args:
        merchant_id: 기준 가맹점 ID (예: M0001)
        top_k: 추천 개수 (기본값: 10)

    Returns:
        유사 가맹점 목록과 유사도 점수
    """
    return tool_recommend_similar_merchants(merchant_id, top_k)


@tool
def search_documents(query: str, top_k: int = 3) -> dict:
    """
    업로드된 PDF/문서에서 용어, 개념, 정의를 검색합니다.
    가맹점 데이터 조회가 아닌, 비즈니스 용어나 개념 설명이 필요할 때 사용합니다.

    사용 예시:
    - "LTV/CAC란 무엇인가?" → query="LTV CAC 정의"
    - "재구매율이 뭐야?" → query="재구매율 정의"
    - "머신러닝 용어 설명" → query="머신러닝 용어"

    주의: 가맹점 순위, 매출 데이터 등은 이 도구가 아닌 다른 도구(rank_merchants 등)를 사용하세요.

    Args:
        query: 검색 질의 (용어, 개념 관련)
        top_k: 검색 결과 개수 (기본값: 3, 최대: 10)

    Returns:
        관련 문서 스니펫과 출처
    """
    return tool_rag_search(query, st.OPENAI_API_KEY, top_k)


# 모든 도구 리스트 (LLM에 바인딩할 때 사용)
ALL_TOOLS = [
    get_merchant_metrics,
    get_merchant_history,
    predict_revenue,
    detect_anomaly,
    classify_growth,
    list_merchants,
    rank_merchants,
    rank_by_dimension,
    compare_industry,
    recommend_for_customer,
    recommend_similar_merchants,
    search_documents,
]
