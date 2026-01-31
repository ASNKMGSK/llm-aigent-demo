import re
from typing import Any, Optional, Tuple

import pandas as pd

from .utils import safe_str
from .constants import DEFAULT_TOPN, MAX_TOPN


def extract_top_k_from_text(user_text: str, default_k: int = DEFAULT_TOPN) -> int:
    """텍스트에서 top-k 숫자 추출 (예: "상위 10개", "top 5")"""
    t = safe_str(user_text)

    # 1) top 10 / top=10 / top_k=10
    m = re.search(r"(?i)\btop\s*[_-]?\s*k?\s*[:=]?\s*(\d{1,3})", t)
    if not m:
        # 2) 상위 10 / TOP10
        m = re.search(r"(?i)(?:상위|top)\s*(\d{1,3})", t)
    if not m:
        # 3) 10개 / 10곳 / 10개 추천
        m = re.search(r"(\d{1,3})\s*(?:개|곳|건|명)", t)

    k = default_k
    if m:
        try:
            k = int(m.group(1))
        except Exception:
            k = default_k

    k = max(1, min(int(k), MAX_TOPN))
    return k


def parse_month_range_from_text(user_text: str) -> Tuple[Optional[str], Optional[str]]:
    """텍스트에서 월 범위 파싱 (예: "2024-01부터 2024-03까지")"""
    t = safe_str(user_text)
    pats = re.findall(r"(20\d{2})\s*[-./]?\s*(\d{1,2})", t)
    if not pats:
        return (None, None)

    months = []
    for y, m in pats:
        mm = int(m)
        if 1 <= mm <= 12:
            months.append(f"{int(y):04d}-{mm:02d}")
    if not months:
        return (None, None)

    if len(months) == 1:
        return (months[0], months[0])

    months = sorted(months)
    return (months[0], months[-1])


def month_to_period(x: Any) -> Optional[pd.Period]:
    """월 문자열을 pandas Period로 변환"""
    s = safe_str(x).strip()
    if not s:
        return None
    try:
        dt = pd.to_datetime(s, errors="coerce")
        if pd.isna(dt):
            s2 = re.sub(r"[^0-9]", "", s)
            dt2 = pd.to_datetime(s2, format="%Y%m", errors="coerce")
            if pd.isna(dt2):
                return None
            return dt2.to_period("M")
        return dt.to_period("M")
    except Exception:
        return None


def filter_metrics_by_month_range(
    df: pd.DataFrame, start_month: Optional[str], end_month: Optional[str]
) -> pd.DataFrame:
    """메트릭 데이터프레임을 월 범위로 필터링"""
    if df is None or len(df) == 0:
        return df
    if "txn_month_dt" not in df.columns:
        return df

    if not start_month and not end_month:
        return df

    sp = month_to_period(start_month) if start_month else None
    ep = month_to_period(end_month) if end_month else None
    if sp is None and ep is None:
        return df

    period = df["txn_month_dt"].dt.to_period("M")
    if sp is not None and ep is not None:
        mask = (period >= sp) & (period <= ep)
    elif sp is not None:
        mask = (period >= sp)
    else:
        mask = (period <= ep)

    return df[mask].copy()


def extract_merchant_id(text: str) -> Optional[str]:
    """텍스트에서 가맹점 ID 추출 (예: M0001)"""
    t = text or ""
    # 숫자 확장 방지: M0001 뒤에 숫자가 더 붙는 케이스만 제외
    m = re.search(r"(?i)(?<![0-9a-zA-Z])(m\d{4})(?!\d)", t)
    if not m:
        # 그래도 못잡으면 그냥 포함 검색(최후 폴백)
        m = re.search(r"(?i)(m\d{4})", t)
        if not m:
            return None
    return m.group(1).upper()


def extract_customer_id(text: str) -> Optional[str]:
    """텍스트에서 고객 ID 추출 (예: C00001)"""
    t = text or ""
    m = re.search(r"(?i)(?<![0-9a-zA-Z])(c\d{5})(?!\d)", t)
    if not m:
        m = re.search(r"(?i)(c\d{5})", t)
        if not m:
            return None
    return m.group(1).upper()


def _norm_key(s: Any) -> str:
    """문자열 정규화 (공백 제거, 소문자 변환)"""
    return re.sub(r"\s+", "", safe_str(s)).lower().strip()


def extract_industry_from_text(user_text: str, industry_norm_map: dict) -> str:
    """텍스트에서 업종명 추출"""
    txt = safe_str(user_text).strip()

    # 패턴 1: "IT 업종"
    m2 = re.search(r"([^\s]+)\s*업종\b", txt)
    if m2:
        cand = safe_str(m2.group(1)).strip()
        if cand:
            nk = _norm_key(cand)
            if nk in industry_norm_map:
                return industry_norm_map[nk]
            return cand

    # 패턴 2: "업종: IT"
    m = re.search(r"\b업종\s*[:=]\s*([^\n\r]+)", txt)
    if m:
        cand = safe_str(m.group(1)).strip()
        cand = re.sub(
            r"(현황|현황분석|현황\s*분석|분석|비교|평균|대비|리포트|보고서|조회)\s*$", "", cand
        ).strip()
        if cand:
            nk = _norm_key(cand)
            if nk in industry_norm_map:
                return industry_norm_map[nk]
            return cand

    # 패턴 3: 업종명이 텍스트에 직접 포함된 경우
    if industry_norm_map:
        vals = list(set(industry_norm_map.values()))
        best = max((v for v in vals if v and (v in txt)), key=len, default="")
        if best:
            return best

    return ""
