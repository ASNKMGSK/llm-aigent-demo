"""
main.py - 애플리케이션 진입점
FastAPI 앱 생성, 미들웨어, startup 이벤트, 라우터 등록
"""
import os

# OpenMP 충돌 방지 (EasyOCR + numpy/sklearn 등)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import traceback

import numpy as np

# numpy 호환성 패치
if not hasattr(np, "NaN"):
    np.NaN = np.nan  # noqa: N816

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import state as st
from api.routes import router as api_router
from data.loader import init_data_models
from rag.service import rag_build_or_load_index

# ============================================================
# 앱 생성
# ============================================================
app = FastAPI(title="LLM & AI AGENT 핀테크 플랫폼", version="2.0.0")

# ============================================================
# CORS
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 요청/응답 로깅 미들웨어
# ============================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        st.logger.info("REQ %s %s", request.method, request.url.path)
        resp = await call_next(request)
        st.logger.info("RES %s %s %s", request.method, request.url.path, resp.status_code)
        return resp
    except Exception:
        st.logger.exception("UNHANDLED %s %s", request.method, request.url.path)
        raise

# ============================================================
# 전역 예외 핸들러
# ============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    st.logger.exception("EXCEPTION %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "status": "FAILED",
            "error": str(exc),
            "trace": traceback.format_exc(),
            "log_file": st.LOG_FILE,
        },
    )

# ============================================================
# 라우터 등록
# ============================================================
app.include_router(api_router)

# ============================================================
# Startup 이벤트
# ============================================================
@app.on_event("startup")
def on_startup():
    st.logger.info("APP_STARTUP")
    st.logger.info("BASE_DIR=%s", st.BASE_DIR)
    st.logger.info("LOG_FILE=%s", st.LOG_FILE)
    st.logger.info("PID=%s", os.getpid())
    try:
        init_data_models()
        _k = st.OPENAI_API_KEY
        if _k:
            rag_build_or_load_index(api_key=_k, force_rebuild=False)
        else:
            st.logger.info("RAG_SKIP_STARTUP no_env_api_key docs_dir=%s", st.RAG_DOCS_DIR)
    except Exception as e:
        st.logger.exception("BOOTSTRAP_FAIL: %s", e)
        raise

# ============================================================
# 직접 실행
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None,
        access_log=True,
    )
