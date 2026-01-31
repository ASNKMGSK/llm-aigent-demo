from typing import List, Dict

import numpy as np
import pandas as pd


def to_numeric_df(x_df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
    """데이터프레임의 feature columns를 numeric으로 변환"""
    out = x_df.copy()
    for c in feature_cols:
        if c not in out.columns:
            out[c] = 0.0
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out[feature_cols].fillna(0.0).astype(float)
    return out


def build_feature_df(row: pd.Series, feature_cols: List[str]) -> pd.DataFrame:
    """Series를 feature DataFrame으로 변환"""
    x_df = row.reindex(feature_cols).to_frame().T
    return to_numeric_df(x_df, feature_cols)


def normalize_importance(values: np.ndarray) -> np.ndarray:
    """Importance 값들을 0-1로 정규화"""
    arr = np.array(values, dtype=float).reshape(-1)
    s = float(arr.sum())
    if s <= 0:
        return np.zeros_like(arr, dtype=float)
    return arr / s


def topk_importance(
    feature_cols: List[str], importances: np.ndarray, top_k: int, label_map: Dict[str, str]
) -> List[dict]:
    """상위 k개의 중요 피처 반환"""
    imp = np.array(importances, dtype=float).reshape(-1)
    if len(imp) != len(feature_cols):
        imp = np.zeros(len(feature_cols), dtype=float)

    norm = normalize_importance(imp)
    rows = []
    for i, f in enumerate(feature_cols):
        rows.append(
            {
                "feature": f,
                "feature_label": label_map.get(f, f),
                "importance": float(imp[i]),
                "importance_pct": round(float(norm[i]) * 100, 4),
            }
        )
    rows.sort(key=lambda r: r["importance"], reverse=True)
    return rows[: int(top_k)]
