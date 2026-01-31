"""
agent/tools.py - 분석 도구 함수들
가맹점 메트릭 조회, 예측, 이상탐지, 성장분류, 추천 등
"""
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd

from core.constants import (
    FEATURE_COLS_REG, FEATURE_COLS_ANOMALY, FEATURE_COLS_CLF,
    FEATURE_LABELS, RECO_COL_USER, RECO_COL_ITEM, DEFAULT_TOPN,
)
from core.utils import safe_str, safe_int, safe_float, json_sanitize
from ml.helpers import to_numeric_df, build_feature_df, normalize_importance, topk_importance
from data.loader import _merge_merchant_meta, _ensure_popular_merchants
import state as st


# ============================================================
# 내부 유틸
# ============================================================
def _latest_row_for_merchant(merchant_id: str) -> Optional[pd.Series]:
    key = safe_str(merchant_id, "").strip()
    return st.LATEST_METRICS_MAP.get(key)


# ============================================================
# 가맹점 메트릭 조회
# ============================================================
def tool_get_merchant_metrics(merchant_id: str) -> dict:
    latest = _latest_row_for_merchant(merchant_id)
    if latest is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}

    return {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "기준월": safe_str(latest.get("txn_month", "")),
        "매출": safe_int(latest.get("total_revenue", 0)),
        "성장률": round(safe_float(latest.get("revenue_growth_rate", 0.0)), 4),
        "객단가": safe_int(latest.get("avg_order_value", 0)),
        "재구매율": round(safe_float(latest.get("repeat_purchase_rate", 0.0)), 4),
        "LTV_CAC": round(safe_float(latest.get("ltv_cac_ratio", 0.0)), 4),
        "업종": safe_str(latest.get("industry", "")),
        "지역": safe_str(latest.get("region", "")),
        "성장유형": safe_str(latest.get("growth_type", "")),
    }


def tool_get_merchant_metrics_history_summary(merchant_id: str, months: int = 6) -> dict:
    key = safe_str(merchant_id).strip()
    data = st.METRICS_BY_MERCHANT.get(key)

    if data is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}

    tail = data.tail(int(months)).copy()

    rows = []
    for _, r in tail.iterrows():
        rows.append({
            "기준월": safe_str(r.get("txn_month", "")),
            "매출": safe_int(r.get("total_revenue", 0)),
            "성장률": round(safe_float(r.get("revenue_growth_rate", 0.0)), 4),
            "거래건수": safe_int(r.get("txn_count", 0)),
            "고객수": safe_int(r.get("unique_customers", 0)),
            "객단가": safe_int(r.get("avg_order_value", 0)),
            "재구매율": round(safe_float(r.get("repeat_purchase_rate", 0.0)), 4),
            "LTV_CAC": round(safe_float(r.get("ltv_cac_ratio", 0.0)), 4),
            "업종": safe_str(r.get("industry", "")),
            "지역": safe_str(r.get("region", "")),
            "성장유형": safe_str(r.get("growth_type", "")),
        })

    rev_list = [x["매출"] for x in rows]
    gr_list = [x["성장률"] for x in rows]
    summary = {
        "기간": f"최근 {len(rows)}개월",
        "매출_최소": int(min(rev_list)) if rev_list else 0,
        "매출_최대": int(max(rev_list)) if rev_list else 0,
        "성장률_최소": float(min(gr_list)) if gr_list else 0.0,
        "성장률_최대": float(max(gr_list)) if gr_list else 0.0,
        "최신_기준월": rows[-1]["기준월"] if rows else "",
    }

    return {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "months": int(months),
        "summary": summary,
        "data": rows,
    }


# ============================================================
# 매출 예측
# ============================================================
def tool_explain_revenue_prediction(merchant_id: str, top_k: int = 5) -> dict:
    latest = _latest_row_for_merchant(merchant_id)
    if latest is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}
    if st.rf_reg is None:
        return {"status": "FAILED", "error": "매출 예측 모델이 로드되지 않았습니다."}

    x_df = build_feature_df(latest, FEATURE_COLS_REG)
    pred0 = float(st.rf_reg.predict(x_df)[0])

    global_imp = getattr(st.rf_reg, "feature_importances_", None)
    if global_imp is None:
        return {"status": "FAILED", "error": "모델에 feature_importances_가 없습니다."}

    top = topk_importance(FEATURE_COLS_REG, np.array(global_imp, dtype=float), top_k, FEATURE_LABELS)

    return {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "model": "RandomForestRegressor",
        "explain_type": "feature_importances",
        "predicted": int(round(pred0)),
        "top_factors": top,
    }


def tool_predict_revenue(merchant_id: str, top_k: int = 5, include_explain: bool = True) -> dict:
    latest = _latest_row_for_merchant(merchant_id)
    if latest is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}
    if st.rf_reg is None:
        return {"status": "FAILED", "error": "매출 예측 모델이 로드되지 않았습니다."}

    cur_rev = safe_float(latest.get("total_revenue", 0.0))
    x_df = build_feature_df(latest, FEATURE_COLS_REG)
    pred = float(st.rf_reg.predict(x_df)[0])

    change_pct = 0.0
    if cur_rev != 0:
        change_pct = float((pred - cur_rev) / cur_rev * 100)

    base = {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "현재매출": int(round(cur_rev)),
        "예측매출": int(round(pred)),
        "변화율": round(float(change_pct), 2),
    }

    if include_explain:
        explain = tool_explain_revenue_prediction(merchant_id, top_k=top_k)
        if explain.get("status") == "SUCCESS":
            base["top_factors"] = explain.get("top_factors", [])
            base["explain_model"] = explain.get("model", "RandomForestRegressor")
            base["explain_type"] = explain.get("explain_type", "feature_importances")

    return base


# ============================================================
# 이상 탐지
# ============================================================
def anomaly_pseudo_permutation_importance(x_df: pd.DataFrame, feature_cols: List[str], top_k: int) -> List[dict]:
    if st.iso_forest is None or st.scaler is None or st.metrics_clean is None or len(st.metrics_clean) == 0:
        return []

    x_df = to_numeric_df(x_df, feature_cols)
    score0 = float(st.iso_forest.decision_function(st.scaler.transform(x_df))[0])

    medians: Dict[str, float] = {}
    for f in feature_cols:
        if f in st.metrics_clean.columns:
            try:
                med_val = pd.to_numeric(st.metrics_clean[f], errors="coerce").median()
                medians[f] = 0.0 if pd.isna(med_val) else float(med_val)
            except Exception:
                medians[f] = 0.0
        else:
            medians[f] = 0.0

    rows = []
    for f in feature_cols:
        x_rep = x_df.copy()
        original_value = safe_float(x_df.iloc[0].get(f, 0.0), 0.0)
        x_rep.loc[:, f] = medians.get(f, 0.0)
        score_r = float(st.iso_forest.decision_function(st.scaler.transform(x_rep))[0])
        drop = max(0.0, score0 - score_r)

        rows.append({
            "feature": f,
            "feature_label": FEATURE_LABELS.get(f, f),
            "original_value": float(original_value),
            "baseline_median": float(medians.get(f, 0.0)),
            "score0": round(float(score0), 6),
            "score_replaced": round(float(score_r), 6),
            "importance": float(drop),
            "importance_pct": 0.0,
        })

    imp = np.array([r["importance"] for r in rows], dtype=float)
    norm = normalize_importance(imp)
    for i, r in enumerate(rows):
        r["importance_pct"] = round(float(norm[i]) * 100, 4)

    rows.sort(key=lambda r: r["importance"], reverse=True)
    return rows[:int(top_k)]


def tool_explain_anomaly_detection(merchant_id: str, top_k: int = 5) -> dict:
    latest = _latest_row_for_merchant(merchant_id)
    if latest is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}
    if st.iso_forest is None or st.scaler is None:
        return {"status": "FAILED", "error": "이상 탐지 모델이 로드되지 않았습니다."}

    x_df = build_feature_df(latest, FEATURE_COLS_ANOMALY)
    x_scaled = st.scaler.transform(x_df)
    pred = int(st.iso_forest.predict(x_scaled)[0])
    score0 = float(st.iso_forest.decision_function(x_scaled)[0])

    top = anomaly_pseudo_permutation_importance(x_df, FEATURE_COLS_ANOMALY, top_k)

    return {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "model": "IsolationForest",
        "explain_type": "pseudo_permutation_importance(median_replace)",
        "result": "이상" if pred == -1 else "정상",
        "score": round(score0, 6),
        "top_factors": top,
    }


def tool_detect_anomaly(merchant_id: str, top_k: int = 5, include_explain: bool = True) -> dict:
    latest = _latest_row_for_merchant(merchant_id)
    if latest is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}
    if st.iso_forest is None or st.scaler is None:
        return {"status": "FAILED", "error": "이상 탐지 모델이 로드되지 않았습니다."}

    x_df = build_feature_df(latest, FEATURE_COLS_ANOMALY)
    x_scaled = st.scaler.transform(x_df)

    pred = int(st.iso_forest.predict(x_scaled)[0])
    base = {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "결과": "이상" if pred == -1 else "정상",
        "점수": round(float(st.iso_forest.decision_function(x_scaled)[0]), 4),
    }

    if include_explain:
        explain = tool_explain_anomaly_detection(merchant_id, top_k=top_k)
        if explain.get("status") == "SUCCESS":
            base["top_factors"] = explain.get("top_factors", [])
            base["explain_model"] = explain.get("model", "IsolationForest")
            base["explain_type"] = explain.get("explain_type", "pseudo_permutation_importance(median_replace)")

    return base


# ============================================================
# 성장 분류
# ============================================================
def tool_explain_growth_classification(merchant_id: str, top_k: int = 5) -> dict:
    latest = _latest_row_for_merchant(merchant_id)
    if latest is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}
    if st.rf_clf is None or st.le_growth is None:
        return {"status": "FAILED", "error": "성장 분류 모델이 로드되지 않았습니다."}

    x_df = build_feature_df(latest, FEATURE_COLS_CLF)
    pred = st.rf_clf.predict(x_df)[0]
    proba = st.rf_clf.predict_proba(x_df)[0]

    pred_label = safe_str(st.le_growth.inverse_transform([pred])[0])
    conf = round(float(max(proba)) * 100, 2)

    global_imp = getattr(st.rf_clf, "feature_importances_", None)
    if global_imp is None:
        return {"status": "FAILED", "error": "모델에 feature_importances_가 없습니다."}

    top = topk_importance(FEATURE_COLS_CLF, np.array(global_imp, dtype=float), top_k, FEATURE_LABELS)

    return {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "model": "RandomForestClassifier",
        "explain_type": "feature_importances",
        "predicted_class": pred_label,
        "confidence": conf,
        "top_factors": top,
    }


def tool_classify_growth(merchant_id: str, top_k: int = 5, include_explain: bool = True) -> dict:
    latest = _latest_row_for_merchant(merchant_id)
    if latest is None:
        return {"status": "FAILED", "error": f"가맹점 {merchant_id} 없음"}
    if st.rf_clf is None or st.le_growth is None:
        return {"status": "FAILED", "error": "성장 분류 모델이 로드되지 않았습니다."}

    x_df = build_feature_df(latest, FEATURE_COLS_CLF)
    pred = st.rf_clf.predict(x_df)[0]
    proba = st.rf_clf.predict_proba(x_df)[0]

    base = {
        "status": "SUCCESS",
        "가맹점ID": safe_str(merchant_id).strip(),
        "성장유형": safe_str(st.le_growth.inverse_transform([pred])[0]),
        "신뢰도": round(float(max(proba)) * 100, 2),
    }

    if include_explain:
        explain = tool_explain_growth_classification(merchant_id, top_k=top_k)
        if explain.get("status") == "SUCCESS":
            base["top_factors"] = explain.get("top_factors", [])
            base["explain_model"] = explain.get("model", "RandomForestClassifier")
            base["explain_type"] = explain.get("explain_type", "feature_importances")

    return base


# ============================================================
# 랭킹
# ============================================================
def tool_rank_dimension(
    dimension: str,
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    top_n: int = DEFAULT_TOPN,
) -> dict:
    from core.parsers import filter_metrics_by_month_range

    if st.metrics_clean is None or len(st.metrics_clean) == 0:
        return {"status": "FAILED", "error": "metrics 데이터가 없습니다."}

    dim = safe_str(dimension).strip()
    if dim not in ("industry", "region", "growth_type"):
        return {"status": "FAILED", "error": f"지원하지 않는 dimension: {dim}"}

    df = filter_metrics_by_month_range(st.metrics_clean, start_month, end_month)

    if dim not in df.columns:
        return {"status": "FAILED", "error": f"{dim} 컬럼이 없습니다."}

    rev = pd.to_numeric(df.get("total_revenue", 0.0), errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    gr = pd.to_numeric(df.get("revenue_growth_rate", 0.0), errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    rr = pd.to_numeric(df.get("repeat_purchase_rate", 0.0), errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)

    tmp = df.assign(_rev=rev, _gr=gr, _rr=rr)

    g = tmp.groupby(tmp[dim].astype(str))
    out = g.agg(
        표본수=("_rev", "size"),
        평균매출=("_rev", "mean"),
        평균성장률=("_gr", "mean"),
        평균재구매율=("_rr", "mean"),
        가맹점수=("merchant_id", "nunique") if "merchant_id" in tmp.columns else ("_rev", "size"),
    ).reset_index().rename(columns={dim: "그룹"})

    out["평균매출"] = out["평균매출"].round(0).astype(int)
    out["평균성장률"] = out["평균성장률"].round(2)
    out["평균재구매율"] = out["평균재구매율"].round(2)
    out = out.sort_values(["평균매출", "표본수"], ascending=[False, False]).head(int(top_n))

    return {
        "status": "SUCCESS",
        "dimension": dim,
        "기간": f"{start_month or '전체'} ~ {end_month or '전체'}",
        "top_n": int(top_n),
        "data": out.to_dict("records"),
    }


def tool_rank_merchants(
    metric: str = "total_revenue",
    start_month: Optional[str] = None,
    end_month: Optional[str] = None,
    top_n: int = DEFAULT_TOPN,
    industry: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """
    가맹점 랭킹. industry/region으로 필터링 가능.
    예: 음식점 업종 Top 10 → industry="음식점", top_n=10
    """
    from core.parsers import filter_metrics_by_month_range

    if st.metrics_clean is None or len(st.metrics_clean) == 0:
        return {"status": "FAILED", "error": "metrics 데이터가 없습니다."}

    m = safe_str(metric).strip()
    if m not in ("total_revenue", "revenue_growth_rate", "repeat_purchase_rate"):
        return {"status": "FAILED", "error": f"지원하지 않는 metric: {m}"}

    df = filter_metrics_by_month_range(st.metrics_clean, start_month, end_month)
    if "merchant_id" not in df.columns:
        return {"status": "FAILED", "error": "merchant_id 컬럼이 없습니다."}

    # 업종 필터
    if industry and "industry" in df.columns:
        industry_clean = safe_str(industry).strip()
        df = df[df["industry"].astype(str).str.strip() == industry_clean]
        if len(df) == 0:
            return {"status": "FAILED", "error": f"'{industry}' 업종에 해당하는 가맹점이 없습니다."}

    # 지역 필터
    if region and "region" in df.columns:
        region_clean = safe_str(region).strip()
        df = df[df["region"].astype(str).str.strip() == region_clean]
        if len(df) == 0:
            return {"status": "FAILED", "error": f"'{region}' 지역에 해당하는 가맹점이 없습니다."}

    val = pd.to_numeric(df.get(m, 0.0), errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    tmp = df.assign(_val=val)

    grp_cols = ["merchant_id"]
    for c in ["merchant_name", "industry", "region", "growth_type"]:
        if c in tmp.columns:
            grp_cols.append(c)

    g = tmp.groupby(grp_cols)["_val"].mean().reset_index().rename(columns={"_val": "평균값"})
    if m == "total_revenue":
        g["평균값"] = g["평균값"].round(0).astype(int)
    else:
        g["평균값"] = g["평균값"].round(2)

    g = g.sort_values("평균값", ascending=False).head(int(top_n))

    filter_desc = []
    if industry:
        filter_desc.append(f"업종={industry}")
    if region:
        filter_desc.append(f"지역={region}")

    return {
        "status": "SUCCESS",
        "metric": m,
        "filter": ", ".join(filter_desc) if filter_desc else "전체",
        "기간": f"{start_month or '전체'} ~ {end_month or '전체'}",
        "top_n": int(top_n),
        "count": len(g),
        "data": g.to_dict("records"),
    }


# ============================================================
# 업종 비교
# ============================================================
def tool_compare_industry(industry: str) -> dict:
    if st.metrics_clean is None or len(st.metrics_clean) == 0:
        return {"status": "FAILED", "error": "metrics 데이터가 없습니다."}

    if "industry" not in st.metrics_clean.columns:
        return {"status": "FAILED", "error": "industry 컬럼이 없습니다."}

    from core.parsers import _norm_key
    raw_industry = safe_str(industry).strip()
    if not raw_industry:
        return {"status": "FAILED", "error": "업종명이 비어 있습니다."}

    available = st.metrics_clean["industry"].astype(str).unique().tolist()

    if raw_industry not in available and st.INDUSTRY_NORM_MAP:
        nk = _norm_key(raw_industry)
        if nk in st.INDUSTRY_NORM_MAP:
            raw_industry = st.INDUSTRY_NORM_MAP[nk]

    if raw_industry not in available:
        return {"status": "FAILED", "error": f"업종 '{industry}' 없음", "가능업종": available}

    data = st.metrics_clean[st.metrics_clean["industry"].astype(str) == raw_industry]
    avg_rev = float(pd.to_numeric(data.get("total_revenue", 0.0), errors="coerce").fillna(0.0).mean())
    avg_gr = float(pd.to_numeric(data.get("revenue_growth_rate", 0.0), errors="coerce").fillna(0.0).mean())
    avg_rr = float(pd.to_numeric(data.get("repeat_purchase_rate", 0.0), errors="coerce").fillna(0.0).mean())

    return {
        "status": "SUCCESS",
        "업종": safe_str(raw_industry),
        "가맹점수": int(data["merchant_id"].nunique()),
        "평균매출": int(round(avg_rev)),
        "평균성장률": round(avg_gr, 2),
        "평균재구매율": round(avg_rr, 2),
    }


# ============================================================
# 추천
# ============================================================
def _normalize_reco_output(df: pd.DataFrame, top_k: int) -> List[dict]:
    if df is None or len(df) == 0:
        return []

    out = df.copy()

    if "prediction" in out.columns and "score" not in out.columns:
        out = out.rename(columns={"prediction": "score"})
    if "relevance" in out.columns and "score" not in out.columns:
        out = out.rename(columns={"relevance": "score"})
    if "col_prediction" in out.columns and "score" not in out.columns:
        out = out.rename(columns={"col_prediction": "score"})

    if RECO_COL_ITEM in out.columns and "merchant_id" not in out.columns:
        out = out.rename(columns={RECO_COL_ITEM: "merchant_id"})
    if "item" in out.columns and "merchant_id" not in out.columns:
        out = out.rename(columns={"item": "merchant_id"})
    if "col_item" in out.columns and "merchant_id" not in out.columns:
        out = out.rename(columns={"col_item": "merchant_id"})
    if "recommended_item" in out.columns and "merchant_id" not in out.columns:
        out = out.rename(columns={"recommended_item": "merchant_id"})

    if "merchant_id" not in out.columns:
        return []

    if "score" not in out.columns:
        out["score"] = 0.0

    out["merchant_id"] = out["merchant_id"].astype(str)
    out["score"] = pd.to_numeric(out["score"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)

    out = out.sort_values("score", ascending=False).head(max(1, int(top_k)))
    out = _merge_merchant_meta(out)

    cols = ["merchant_id", "merchant_name", "industry", "region", "growth_type", "score"]
    cols = [c for c in cols if c in out.columns]
    return json_sanitize(out[cols].to_dict("records")) or []


def tool_recommend_merchants_for_customer(customer_id: str, top_k: int = 10) -> dict:
    from rag.service import SAR_AVAILABLE, SARSingleNode

    if not SAR_AVAILABLE or SARSingleNode is None:
        return {"status": "FAILED", "error": "recommenders 패키지가 없습니다. (pip install recommenders)"}

    if st.sar_model is None:
        return {"status": "FAILED", "error": "추천 모델(model_reco.pkl)이 로드되지 않았습니다."}

    cid = safe_str(customer_id).strip().upper()
    if not cid:
        return {"status": "FAILED", "error": "customer_id가 비어 있습니다."}

    k = max(1, int(top_k))

    has_user = False
    try:
        user_map = getattr(st.sar_model, "user2index", None)
        if isinstance(user_map, dict) and cid in user_map:
            has_user = True
    except Exception:
        has_user = False

    if not has_user:
        recs = _ensure_popular_merchants(top_k=k)
        return {"status": "SUCCESS", "type": "popularity_fallback", "customer_id": cid, "top_k": k, "data": recs}

    try:
        user_df = pd.DataFrame({RECO_COL_USER: [cid]})
        rec_df = st.sar_model.recommend_k_items(user_df, top_k=k, sort_top_k=True, remove_seen=True)
        recs = _normalize_reco_output(rec_df, top_k=k)
        return {"status": "SUCCESS", "type": "sar_user_reco", "customer_id": cid, "top_k": k, "data": recs}
    except Exception as e:
        return {"status": "FAILED", "error": f"SAR 추천 실패: {safe_str(e)}", "customer_id": cid, "top_k": k}


def tool_recommend_similar_merchants(seed_merchant_id: str, top_k: int = 10) -> dict:
    from rag.service import SAR_AVAILABLE, SARSingleNode

    if not SAR_AVAILABLE or SARSingleNode is None:
        return {"status": "FAILED", "error": "recommenders 패키지가 없습니다. (pip install recommenders)"}

    if st.sar_model is None:
        return {"status": "FAILED", "error": "추천 모델(model_reco.pkl)이 로드되지 않았습니다."}

    mid = safe_str(seed_merchant_id).strip().upper()
    if not mid:
        return {"status": "FAILED", "error": "merchant_id가 비어 있습니다."}

    k = max(1, int(top_k))

    try:
        seed_df = pd.DataFrame({RECO_COL_ITEM: [mid]})
        rec_df = st.sar_model.get_item_based_topk(seed_df, top_k=k, sort_top_k=True)
        recs = _normalize_reco_output(rec_df, top_k=k)
        return {"status": "SUCCESS", "type": "sar_item_similarity", "merchant_id": mid, "top_k": k, "data": recs}
    except Exception as e:
        return {"status": "FAILED", "error": f"SAR 유사 가맹점 실패: {safe_str(e)}", "merchant_id": mid, "top_k": k}


# ============================================================
# 전체 가맹점 목록
# ============================================================
def tool_list_merchants(summary_only: bool = True) -> dict:
    """
    전체 가맹점 목록 반환.
    summary_only=True (기본값): 목록 없이 요약(업종별/지역별/성장유형별 집계)만 반환.
    summary_only=False: 전체 목록도 포함.
    """
    if st.metrics_clean is None or len(st.metrics_clean) == 0:
        return {"status": "FAILED", "error": "metrics 데이터가 없습니다."}

    cols = ["merchant_id", "merchant_name", "industry", "region", "growth_type"]
    safe_cols = [c for c in cols if c in st.metrics_clean.columns]

    if not st.LATEST_METRICS_MAP:
        return {
            "status": "SUCCESS", "count": 0,
            "summary_by_industry": [], "summary_by_region": [], "summary_by_growth_type": [],
        }

    cached_latest = pd.DataFrame(list(st.LATEST_METRICS_MAP.values()))

    if len(safe_cols) == 0:
        merchant_list = [{"merchant_id": safe_str(x)} for x in cached_latest["merchant_id"].unique().tolist()]
    else:
        merchant_list = cached_latest[safe_cols].drop_duplicates().to_dict("records")

    def _count_by(col_name: str, label_key: str) -> List[dict]:
        if col_name not in cached_latest.columns:
            return []
        s = cached_latest[col_name].astype(str).fillna("").replace("", "미분류")
        vc = s.value_counts(dropna=False)
        return [{label_key: str(k), "가맹점수": int(v)} for k, v in vc.items()]

    result = {
        "status": "SUCCESS",
        "count": int(len(merchant_list)),
        "summary_by_industry": _count_by("industry", "업종"),
        "summary_by_region": _count_by("region", "지역"),
        "summary_by_growth_type": _count_by("growth_type", "성장유형"),
    }

    if not summary_only:
        result["list"] = merchant_list

    return result


# ============================================================
# 체크리스트 / 리포트 생성
# ============================================================
def build_checklist_from_metrics(latest: pd.Series) -> List[str]:
    if latest is None:
        return ["데이터 없음"]

    rev = safe_float(latest.get("total_revenue", 0.0), 0.0)
    gr = safe_float(latest.get("revenue_growth_rate", 0.0), 0.0)
    aov = safe_float(latest.get("avg_order_value", 0.0), 0.0)
    rr = safe_float(latest.get("repeat_purchase_rate", 0.0), 0.0)
    txn = safe_float(latest.get("txn_count", 0.0), 0.0)
    ltv = safe_float(latest.get("ltv_cac_ratio", 0.0), 0.0)

    checks = []
    if gr <= -20:
        checks.append("성장률이 큰 폭으로 하락했습니다. 전월 대비 거래건수/객단가 중 어느 쪽이 더 크게 변했는지 우선 점검하세요.")
    elif gr >= 20:
        checks.append("성장률이 큰 폭으로 상승했습니다. 일시적 급증(프로모션/대량결제)인지 지속 추세인지 거래건수/객단가로 분해해 점검하세요.")
    else:
        checks.append("성장률 변동이 크지 않습니다. 추세 유지 여부를 3개월 이동평균과 함께 점검하세요.")

    if aov >= 60000:
        checks.append("객단가가 상대적으로 높습니다. 고가 상품 비중 증가/단가 오류/비정상 결제(대량)가 있는지 점검하세요.")
    if txn <= 5:
        checks.append("거래건수가 낮습니다. 유입(신규 고객) 감소 또는 결제 성공률/채널 이슈를 우선 점검하세요.")

    if rr <= 5:
        checks.append("재구매율이 낮습니다. 신규 고객 비중 증가인지, 재방문 유도(쿠폰/CRM) 부재인지 점검하세요.")
    if ltv <= 2.0:
        checks.append("LTV/CAC 비율이 낮은 편입니다. CAC 추정치가 급증했는지, 또는 객단가/재구매율이 낮은지 분해 점검하세요.")

    if rev <= 0:
        checks.append("매출이 0에 가깝습니다. 해당 월 데이터 누락/집계 실패/상태(성공 거래만 집계) 조건을 점검하세요.")

    return checks[:8]


def build_list_merchants_report(list_result: dict) -> str:
    lines: List[str] = []
    lines.append("요청 유형: 전체 가맹점 목록")
    lines.append("대상: 전체")
    lines.append("기준월/기간: 데이터 기준")
    lines.append("")
    lines.append("1) 요약")
    lines.append(f"- 총 가맹점 수: {safe_int(list_result.get('count', 0))}")
    lines.append("")
    lines.append("2) 집계")
    ind = list_result.get("summary_by_industry") or []
    reg = list_result.get("summary_by_region") or []
    gro = list_result.get("summary_by_growth_type") or []

    if ind:
        lines.append("- 업종별 가맹점수")
        for r in ind:
            lines.append(f"  - {safe_str(r.get('업종'))}: {safe_int(r.get('가맹점수'))}")
    else:
        lines.append("- 업종별 집계: 데이터 없음")

    if reg:
        lines.append("- 지역별 가맹점수")
        for r in reg:
            lines.append(f"  - {safe_str(r.get('지역'))}: {safe_int(r.get('가맹점수'))}")
    else:
        lines.append("- 지역별 집계: 데이터 없음")

    if gro:
        lines.append("- 성장유형별 가맹점수")
        for r in gro:
            lines.append(f"  - {safe_str(r.get('성장유형'))}: {safe_int(r.get('가맹점수'))}")
    else:
        lines.append("- 성장유형별 집계: 데이터 없음")

    # 목록이 있을 때만 목록 섹션 출력 (summary_only=True면 list 없음)
    lst = list_result.get("list")
    if lst:
        lines.append("")
        lines.append("3) 목록")
        for x in lst:
            mid = safe_str(x.get("merchant_id", "")).strip()
            name = safe_str(x.get("merchant_name", "")).strip()
            industry = safe_str(x.get("industry", "")).strip()
            region = safe_str(x.get("region", "")).strip()
            growth = safe_str(x.get("growth_type", "")).strip()
            lines.append(f"- {mid}, {name}, 업종: {industry}, 지역: {region}, 성장유형: {growth}")

    return "\n".join(lines).strip()


def build_fallback_report_from_results(results: Dict[str, Any]) -> str:
    m = results.get("get_merchant_metrics")
    hist = results.get("get_merchant_metrics_history_summary")
    pred = results.get("predict_revenue")
    anom = results.get("detect_anomaly")
    grow = results.get("classify_growth")

    lines: List[str] = []
    lines.append("### 분석 리포트(폴백)")
    lines.append("")
    lines.append("#### 1) 결과 요약")

    if isinstance(m, dict) and m.get("status") == "SUCCESS":
        for key in ["가맹점ID", "기준월", "매출", "성장률", "객단가", "재구매율", "LTV_CAC", "업종", "지역", "성장유형"]:
            lines.append(f"- {key}: {m.get(key, '')}")
    elif isinstance(pred, dict) and pred.get("status") == "SUCCESS":
        lines.append(f"- 가맹점ID: {pred.get('가맹점ID', '')}")
        lines.append(f"- 현재매출: {pred.get('현재매출', '')}")
        lines.append(f"- 예측매출(다음 달): {pred.get('예측매출', '')}")
        lines.append(f"- 변화율(%): {pred.get('변화율', '')}")
    else:
        lines.append("- 조회 가능한 결과가 없습니다.")

    lines.append("")
    lines.append("#### 2) 최근 추이 요약")
    if isinstance(hist, dict) and hist.get("status") == "SUCCESS" and isinstance(hist.get("summary"), dict):
        s = hist["summary"]
        lines.append(f"- 기간: {s.get('기간', '')}")
        lines.append(f"- 매출 범위: {s.get('매출_최소', '')} ~ {s.get('매출_최대', '')}")
        lines.append(f"- 성장률 범위: {s.get('성장률_최소', '')} ~ {s.get('성장률_최대', '')}")
        lines.append(f"- 최신 기준월: {s.get('최신_기준월', '')}")
    else:
        lines.append("- 추이 요약 결과가 없습니다.")

    lines.append("")
    lines.append("#### 3) 예측/이상/분류 결과(가능한 범위)")
    if isinstance(pred, dict) and pred.get("status") == "SUCCESS":
        lines.append(f"- 매출 예측: {pred.get('예측매출', '')}")
        lines.append(f"- 변화율(%): {pred.get('변화율', '')}")
    else:
        lines.append("- 매출 예측 결과 없음")

    if isinstance(anom, dict) and anom.get("status") == "SUCCESS":
        lines.append(f"- 이상 탐지 결과: {anom.get('결과', '')}")
        lines.append(f"- 이상 탐지 점수: {anom.get('점수', '')}")
    else:
        lines.append("- 이상 탐지 결과 없음")

    if isinstance(grow, dict) and grow.get("status") == "SUCCESS":
        lines.append(f"- 성장 분류: {grow.get('성장유형', '')}")
        lines.append(f"- 성장 분류 신뢰도: {grow.get('신뢰도', '')}")
    else:
        lines.append("- 성장 분류 결과 없음")

    def pick_top_factors(obj: Any):
        if isinstance(obj, dict):
            tf = obj.get("top_factors")
            if isinstance(tf, list) and tf:
                return tf
        return None

    lines.append("")
    lines.append("#### 4) 모델이 참고한 주요 참고 변수(상위)")
    top_vars = None
    if isinstance(pred, dict) and pred.get("status") == "SUCCESS":
        top_vars = pick_top_factors(pred)

    if top_vars:
        for r in top_vars:
            label = r.get("feature_label") or r.get("feature") or ""
            pct = r.get("importance_pct")
            if pct is not None:
                lines.append(f"- {label}: {pct}%")
            else:
                lines.append(f"- {label}")
    else:
        lines.append("- 중요 변수 정보가 없습니다.")

    lines.append("")
    lines.append("#### 5) 안내")
    lines.append("- 최종 텍스트 생성이 비어 있거나 예외가 발생하여, 내부 결과만으로 리포트를 구성했습니다.")
    return "\n".join(lines).strip()
