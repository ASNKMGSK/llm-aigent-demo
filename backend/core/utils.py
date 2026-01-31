import math
from typing import Any, Dict

import numpy as np
import pandas as pd

# recommenders가 np.NaN을 참조하는 케이스 방어
if not hasattr(np, "NaN"):
    np.NaN = np.nan  # noqa: N816


def safe_str(x: Any, default: str = "") -> str:
    """안전한 문자열 변환"""
    try:
        if x is None:
            return default
        return str(x)
    except Exception:
        return default


def safe_float(x: Any, default: float = 0.0) -> float:
    """안전한 float 변환"""
    try:
        v = pd.to_numeric(x, errors="coerce")
        if pd.isna(v):
            return float(default)
        fv = float(v)
        if not math.isfinite(fv):
            return float(default)
        return fv
    except Exception:
        return float(default)


def safe_int(x: Any, default: int = 0) -> int:
    """안전한 int 변환"""
    try:
        v = pd.to_numeric(x, errors="coerce")
        if pd.isna(v):
            return int(default)
        return int(round(float(v)))
    except Exception:
        return int(default)


def json_sanitize(obj: Any):
    """JSON 직렬화를 위한 객체 변환"""
    if obj is None:
        return None

    if isinstance(obj, (bool, int, str)):
        return obj

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None

    if isinstance(obj, (np.generic,)):
        try:
            return json_sanitize(obj.item())
        except Exception:
            return None

    if isinstance(obj, (pd.Timestamp,)):
        if pd.isna(obj):
            return None
        return obj.isoformat()

    if isinstance(obj, (np.ndarray,)):
        return [json_sanitize(x) for x in obj.tolist()]

    if isinstance(obj, pd.Series):
        return {str(k): json_sanitize(v) for k, v in obj.to_dict().items()}

    if isinstance(obj, pd.DataFrame):
        return [json_sanitize(x) for x in obj.to_dict("records")]

    if isinstance(obj, dict):
        return {str(k): json_sanitize(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [json_sanitize(x) for x in obj]

    try:
        return json_sanitize(vars(obj))
    except Exception:
        return str(obj)


def format_exception(e: Exception) -> Dict[str, Any]:
    """예외를 딕셔너리로 변환"""
    return {"type": type(e).__name__, "message": safe_str(e)}


def format_openai_error(e: Exception) -> Dict[str, Any]:
    """OpenAI 에러를 딕셔너리로 변환"""
    err = {"type": type(e).__name__, "message": str(e)}
    try:
        resp = getattr(e, "response", None)
        if resp is not None:
            err["status_code"] = getattr(resp, "status_code", None)
            err["response_text"] = getattr(resp, "text", None)
    except Exception:
        pass
    return err


def normalize_model_name(model_name: str) -> str:
    """모델명 정규화"""
    m = safe_str(model_name).strip()
    ml = m.lower().replace(" ", "")
    if ml in ("gpt4", "gpt-4", "gpt-4-turbo", "gpt-4turbo", "gpt-4.0", "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"):
        if ml in ("gpt4", "gpt-4", "gpt-4-turbo", "gpt-4turbo", "gpt-4.0"):
            return "gpt-4o"
        return m
    if ml.startswith("gpt-4"):
        return m
    return "gpt-4o"
