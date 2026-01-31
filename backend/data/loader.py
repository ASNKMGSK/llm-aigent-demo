"""
data/loader.py - 데이터/모델 로드 및 초기화
CSV 데이터 로드, ML 모델 로드, 캐시 구성
"""
import os
from typing import Tuple

import joblib
import pandas as pd

from core.utils import safe_str
from core.parsers import _norm_key
import state as st


def safe_label_encode(le, series: pd.Series) -> pd.Series:
    classes = [str(x) for x in getattr(le, "classes_", [])]
    mapping = {c: i for i, c in enumerate(classes)}
    return series.astype(str).map(mapping).fillna(0).astype(int)


def load_dataframes() -> Tuple[pd.DataFrame, pd.DataFrame]:
    merchants_df = pd.read_csv(os.path.join(st.BASE_DIR, "merchants.csv"))
    metrics_df = pd.read_csv(os.path.join(st.BASE_DIR, "metrics.csv"))

    if "merchant_id" not in metrics_df.columns:
        raise RuntimeError("metrics.csv에 merchant_id 컬럼이 없습니다.")

    if "merchant_id" in merchants_df.columns:
        merchants_df["merchant_id"] = merchants_df["merchant_id"].astype(str).str.strip()
    metrics_df["merchant_id"] = metrics_df["merchant_id"].astype(str).str.strip()

    if "txn_month" in metrics_df.columns:
        raw = metrics_df["txn_month"].astype(str).str.strip()
        dt1 = pd.to_datetime(raw, errors="coerce")

        import re
        raw2 = raw.str.replace(r"[^0-9]", "", regex=True)
        dt2 = pd.to_datetime(raw2, format="%Y%m", errors="coerce")

        metrics_df["txn_month_dt"] = dt1.fillna(dt2)
        metrics_df["month_num"] = metrics_df["txn_month_dt"].dt.month.fillna(0).astype(int)
    else:
        metrics_df["txn_month"] = ""
        metrics_df["txn_month_dt"] = pd.NaT
        metrics_df["month_num"] = 0

    metrics_df = metrics_df.sort_values(["merchant_id", "txn_month_dt"], na_position="last").reset_index(drop=True)

    if "total_revenue" not in metrics_df.columns:
        metrics_df["total_revenue"] = 0.0

    for lag in (1, 2, 3):
        metrics_df[f"revenue_lag_{lag}"] = metrics_df.groupby("merchant_id")["total_revenue"].shift(lag)

    metrics_df["revenue_rolling_mean_3"] = metrics_df.groupby("merchant_id")["total_revenue"].transform(
        lambda s: s.rolling(3, min_periods=1).mean()
    )

    if "txn_count" not in metrics_df.columns:
        metrics_df["txn_count"] = 0.0

    metrics_df["txn_rolling_mean_3"] = metrics_df.groupby("merchant_id")["txn_count"].transform(
        lambda s: s.rolling(3, min_periods=1).mean()
    )

    return merchants_df, metrics_df


def load_models_bundle():
    rf_reg_m = joblib.load(os.path.join(st.BASE_DIR, "model_revenue.pkl"))
    iso_forest_m = joblib.load(os.path.join(st.BASE_DIR, "model_anomaly.pkl"))
    rf_clf_m = joblib.load(os.path.join(st.BASE_DIR, "model_growth.pkl"))
    scaler_m = joblib.load(os.path.join(st.BASE_DIR, "scaler.pkl"))
    le_industry_m = joblib.load(os.path.join(st.BASE_DIR, "le_industry.pkl"))
    le_region_m = joblib.load(os.path.join(st.BASE_DIR, "le_region.pkl"))
    le_growth_m = joblib.load(os.path.join(st.BASE_DIR, "le_growth.pkl"))

    sar_m = None
    reco_path = os.path.join(st.BASE_DIR, "model_reco.pkl")
    if os.path.exists(reco_path):
        try:
            sar_m = joblib.load(reco_path)
        except Exception as e:
            st.logger.warning("RECO_MODEL_LOAD_FAIL path=%s err=%s", reco_path, safe_str(e))
            sar_m = None

    return rf_reg_m, iso_forest_m, rf_clf_m, scaler_m, le_industry_m, le_region_m, le_growth_m, sar_m


def _ensure_popular_merchants(top_k: int = 50):
    """콜드스타트 폴백: 인기 가맹점 캐시 구성"""
    import numpy as np
    from core.utils import json_sanitize

    k = max(1, int(top_k))
    if st.POPULAR_MERCHANTS and len(st.POPULAR_MERCHANTS) >= k:
        return st.POPULAR_MERCHANTS[:k]

    if st.metrics_clean is None or len(st.metrics_clean) == 0 or "merchant_id" not in st.metrics_clean.columns:
        st.POPULAR_MERCHANTS = []
        return []

    try:
        latest_df = pd.DataFrame(list(st.LATEST_METRICS_MAP.values())) if st.LATEST_METRICS_MAP else st.metrics_clean.copy()
    except Exception:
        latest_df = st.metrics_clean.copy()

    if "total_revenue" in latest_df.columns:
        s = pd.to_numeric(latest_df["total_revenue"], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
        tmp = latest_df.assign(_rev=s).groupby(latest_df["merchant_id"].astype(str))["_rev"].mean().sort_values(ascending=False).head(max(50, k))
        pop_ids = [str(x) for x in tmp.index.tolist()]
        df = pd.DataFrame({"merchant_id": pop_ids, "score": tmp.values.astype(float)})
    else:
        pop_ids = [str(x) for x in latest_df["merchant_id"].astype(str).dropna().unique().tolist()][:max(50, k)]
        df = pd.DataFrame({"merchant_id": pop_ids, "score": np.linspace(1.0, 0.5, num=len(pop_ids))})

    df["merchant_id"] = df["merchant_id"].astype(str)
    df = _merge_merchant_meta(df)

    cols = ["merchant_id", "merchant_name", "industry", "region", "growth_type", "score"]
    cols = [c for c in cols if c in df.columns]
    st.POPULAR_MERCHANTS = json_sanitize(df[cols].head(max(50, k)).to_dict("records")) or []
    return st.POPULAR_MERCHANTS[:k]


def _merge_merchant_meta(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return df
    if st.merchants is None or len(st.merchants) == 0:
        return df
    if "merchant_id" not in df.columns or "merchant_id" not in st.merchants.columns:
        return df

    meta_cols = ["merchant_id", "merchant_name", "industry", "region", "growth_type"]
    keep = [c for c in meta_cols if c in st.merchants.columns]
    if not keep:
        return df

    mm = st.merchants[keep].drop_duplicates()
    return df.merge(mm, on="merchant_id", how="left")


def init_data_models() -> None:
    """데이터 로드 및 모델 초기화 (startup 시 호출)"""
    st.merchants, st.metrics_clean = load_dataframes()
    st.rf_reg, st.iso_forest, st.rf_clf, st.scaler, st.le_industry, st.le_region, st.le_growth, st.sar_model = load_models_bundle()

    if "industry" in st.metrics_clean.columns and st.le_industry is not None:
        st.metrics_clean["industry_encoded"] = safe_label_encode(st.le_industry, st.metrics_clean["industry"])
    else:
        st.metrics_clean["industry_encoded"] = 0

    if "region" in st.metrics_clean.columns and st.le_region is not None:
        st.metrics_clean["region_encoded"] = safe_label_encode(st.le_region, st.metrics_clean["region"])
    else:
        st.metrics_clean["region_encoded"] = 0

    if "growth_type" in st.metrics_clean.columns and st.le_growth is not None:
        st.metrics_clean["growth_encoded"] = safe_label_encode(st.le_growth, st.metrics_clean["growth_type"])
    else:
        st.metrics_clean["growth_encoded"] = 0

    st.METRICS_BY_MERCHANT = {}
    for mid, group in st.metrics_clean.groupby("merchant_id"):
        st.METRICS_BY_MERCHANT[str(mid)] = group

    st.LATEST_METRICS_MAP = {}
    latest_df = st.metrics_clean.groupby("merchant_id").tail(1)
    for _, row in latest_df.iterrows():
        st.LATEST_METRICS_MAP[str(row["merchant_id"])] = row

    st.INDUSTRY_NORM_MAP = {}
    if st.metrics_clean is not None and len(st.metrics_clean) and "industry" in st.metrics_clean.columns:
        inds = st.metrics_clean["industry"].astype(str).fillna("").unique().tolist()
        st.INDUSTRY_NORM_MAP = {_norm_key(x): safe_str(x).strip() for x in inds if safe_str(x).strip()}

    st.POPULAR_MERCHANTS = _ensure_popular_merchants(top_k=100)

    st.logger.info(
        "DATA_MODELS_READY merchants=%s metrics=%s cached=%s industries=%s reco_ready=%s popular=%s",
        len(st.merchants),
        len(st.metrics_clean),
        len(st.LATEST_METRICS_MAP),
        len(st.INDUSTRY_NORM_MAP),
        bool(st.sar_model is not None),
        len(st.POPULAR_MERCHANTS),
    )
