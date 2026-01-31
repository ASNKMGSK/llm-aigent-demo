# LLM & AI AGENT 핀테크 플랫폼 - Backend

FastAPI 기반 AI 에이전트 분석 플랫폼 백엔드 (리팩토링 완료)

## 목차
- [프로젝트 구조](#프로젝트-구조)
- [주요 기능](#주요-기능)
- [Advanced RAG](#advanced-rag-검색-고도화)
- [ML 모델](#ml-모델)
- [MLOps](#mlops-mlflow)
- [시작하기](#시작하기)
- [사용 예시](#사용-예시)
- [FAQ](#faq)

## 주요 기능

- **AI 에이전트**: LangChain 기반 Tool Calling, 스트리밍 응답
- **ML 분석**: 매출 예측, 이상 탐지, 성장 분류, 추천 시스템
- **Advanced RAG**: Hybrid Search (BM25 + Vector), Reranking, GraphRAG
- **MLOps**: MLflow 실험 추적, 모델 레지스트리, 버전 관리
- **OCR**: 이미지 텍스트 추출 및 RAG 연동

## 프로젝트 구조

```
backend/
├── main.py                 # FastAPI 앱 진입점 (CORS, 미들웨어, startup)
├── state.py                # 전역 상태 관리 (설정, 로깅, 캐시, 모델 참조)
│
├── core/                   # 핵심 유틸리티
│   ├── __init__.py
│   ├── constants.py        # ML Feature columns, 모델 메타데이터, 시스템 프롬프트
│   ├── memory.py           # 대화 메모리 관리 (get/append/clear)
│   ├── parsers.py          # 텍스트 파싱 (ID 추출, 월 범위, top-k)
│   └── utils.py            # 유틸리티 (safe_*, json_sanitize, normalize_model_name)
│
├── ml/                     # ML 헬퍼
│   ├── __init__.py
│   └── helpers.py          # to_numeric_df, build_feature_df, topk_importance
│
├── data/                   # 데이터 로딩
│   ├── __init__.py
│   └── loader.py           # CSV/모델 로드, 캐시 구성, init_data_models()
│
├── rag/                    # RAG 서비스
│   ├── __init__.py
│   ├── service.py          # FAISS 인덱싱, 검색, 파일 관리
│   └── graph_rag.py        # GraphRAG (LLM 기반 엔티티/관계 추출)
│
├── agent/                  # AI 에이전트
│   ├── __init__.py
│   ├── tools.py            # 분석 도구 함수 (metrics, predict, anomaly, growth, rank, reco)
│   ├── tool_schemas.py     # LangChain @tool 정의 (Tool Calling용)
│   ├── intent.py           # 인텐트 감지, 결정적 도구 라우팅 (스트리밍용)
│   ├── llm.py              # LangChain LLM 호출, 메시지 빌더
│   └── runner.py           # Tool Calling 에이전트 실행기
│
├── api/                    # API 라우트
│   ├── __init__.py
│   └── routes.py           # FastAPI 엔드포인트 (APIRouter)
│
├── merchants.csv           # 가맹점 마스터 데이터
├── metrics.csv             # 가맹점별 월별 지표 데이터
├── model_revenue.pkl       # 매출 예측 모델 (Random Forest Regressor)
├── model_anomaly.pkl       # 이상 탐지 모델 (Isolation Forest)
├── model_growth.pkl        # 성장 분류 모델 (Random Forest Classifier)
├── model_reco.pkl          # 추천 모델 (SAR)
├── scaler.pkl              # 데이터 스케일러
├── le_*.pkl                # 라벨 인코더 (industry, region, growth)
├── rag_docs/               # RAG 문서 저장소
├── rag_faiss/              # FAISS 벡터 인덱스
└── logs/                   # 애플리케이션 로그
```

## 모듈 설명

### main.py
- FastAPI 앱 생성 및 설정
- CORS 미들웨어
- 요청/응답 로깅 미들웨어
- 전역 예외 핸들러
- Startup 이벤트 (데이터/모델/RAG 초기화)

### state.py
- 경로 설정 (BASE_DIR, LOG_DIR)
- 로깅 설정
- OpenAI API 키
- 사용자 DB (메모리)
- DataFrame 참조 (merchants, metrics_clean)
- 캐시 (LATEST_METRICS_MAP, METRICS_BY_MERCHANT, INDUSTRY_NORM_MAP)
- ML 모델 참조 (rf_reg, iso_forest, rf_clf, scaler, label encoders)
- 추천 시스템 (sar_model, POPULAR_MERCHANTS)
- RAG 설정/상태 (RAG_STORE, locks)
- 컨텍스트 재사용 (LAST_CONTEXT_STORE)

### core/constants.py
- `FEATURE_COLS_REG` - 매출 예측 피처
- `FEATURE_COLS_ANOMALY` - 이상 탐지 피처
- `FEATURE_COLS_CLF` - 성장 분류 피처
- `FEATURE_LABELS` - 피처 한글 라벨
- `ML_MODEL_INFO` - 모델 메타데이터
- `RAG_DOCUMENTS` - 용어 사전
- `DEFAULT_SYSTEM_PROMPT` - LLM 시스템 프롬프트
- 설정값 (MAX_MEMORY_TURNS, DEFAULT_TOPN, SUMMARY_TRIGGERS 등)

### core/memory.py
- `get_user_memory()` - 사용자별 메모리 deque 반환
- `memory_messages()` - 대화 히스토리 리스트 반환
- `append_memory()` - 대화 내용 추가
- `clear_memory()` - 메모리 초기화

### core/parsers.py
- `extract_top_k_from_text()` - "상위 10개" -> 10
- `parse_month_range_from_text()` - 월 범위 파싱
- `extract_merchant_id()` - "M0001" 추출
- `extract_customer_id()` - "C00001" 추출
- `extract_industry_from_text()` - 업종명 추출
- `filter_metrics_by_month_range()` - DataFrame 월 필터링

### core/utils.py
- `safe_str()`, `safe_float()`, `safe_int()` - 안전한 타입 변환
- `json_sanitize()` - JSON 직렬화용 객체 변환
- `format_openai_error()` - OpenAI 에러 포맷팅
- `normalize_model_name()` - 모델명 정규화

### ml/helpers.py
- `to_numeric_df()` - DataFrame을 numeric으로 변환
- `build_feature_df()` - Series를 feature DataFrame으로 변환
- `normalize_importance()` - Importance 정규화
- `topk_importance()` - 상위 k개 중요 피처 반환

### ml/mlflow_tracker.py
MLflow 실험 추적 유틸리티:
- `init_mlflow()` - MLflow 초기화
- `MLflowExperiment` - 컨텍스트 매니저
- `log_params()`, `log_metrics()` - 파라미터/메트릭 로깅
- `log_model_sklearn()` - 모델 로깅 및 레지스트리 등록

### ml/train_models.py
모델 학습 스크립트 (MLflow 추적):
- `train_revenue_model()` - 매출 예측 모델
- `train_anomaly_model()` - 이상 탐지 모델
- `train_growth_model()` - 성장 분류 모델

### data/loader.py
- `load_dataframes()` - CSV 로드, lag/rolling 피처 생성
- `load_models_bundle()` - ML 모델 로드
- `init_data_models()` - 전체 초기화 (startup 시 호출)
- `_ensure_popular_merchants()` - 인기 가맹점 캐시

### rag/service.py
- `rag_build_or_load_index()` - FAISS 인덱스 구축/로드 + BM25 + Knowledge Graph
- `rag_search_local()` - 로컬 문서 검색 (Vector)
- `rag_search_hybrid()` - **Hybrid Search (BM25 + Vector + Reranking)**
- `rag_search_glossary()` - 용어 사전 검색
- `tool_rag_search()` - 통합 RAG 검색
- 파일 관리 (업로드, 삭제, 상태 확인)
- 한글 경로 우회 (`_safe_faiss_save`, `_safe_faiss_load`)

**Advanced RAG Features:**
- `_build_bm25_index()` - BM25 키워드 인덱스 구축
- `_bm25_search()` - BM25 키워드 검색
- `_rerank_results()` - Cross-Encoder 재정렬
- `_reciprocal_rank_fusion()` - BM25 + Vector 점수 융합
- `build_knowledge_graph()` - Knowledge Graph 구축
- `search_knowledge_graph()` - Knowledge Graph 검색

### agent/tools.py
분석 도구 함수:
- `tool_get_merchant_metrics()` - 가맹점 현황
- `tool_get_merchant_metrics_history_summary()` - 가맹점 이력 요약
- `tool_predict_revenue()` - 매출 예측
- `tool_explain_revenue_prediction()` - 매출 예측 설명
- `tool_detect_anomaly()` - 이상 탐지
- `tool_explain_anomaly_detection()` - 이상 탐지 설명
- `tool_classify_growth()` - 성장 분류
- `tool_explain_growth_classification()` - 성장 분류 설명
- `tool_rank_dimension()` - 업종/지역/성장유형별 집계 통계
- `tool_rank_merchants()` - 가맹점 순위 (industry/region 필터 지원)
- `tool_compare_industry()` - 업종 비교
- `tool_recommend_merchants_for_customer()` - 고객별 추천
- `tool_recommend_similar_merchants()` - 유사 가맹점 추천
- `tool_list_merchants()` - 가맹점 목록 (summary_only 지원)
- 리포트 빌더 함수

### agent/tool_schemas.py
LangChain Tool Calling을 위한 도구 정의:
- `get_merchant_metrics` - 가맹점 현황 조회
- `get_merchant_history` - 가맹점 이력 조회
- `predict_revenue` - 매출 예측
- `detect_anomaly` - 이상 탐지
- `classify_growth` - 성장 분류
- `list_merchants` - 가맹점 목록/요약
- `rank_merchants` - 가맹점 순위 (업종/지역 필터 지원)
- `rank_by_dimension` - 업종별/지역별 집계 통계
- `compare_industry` - 업종 비교
- `recommend_for_customer` - 고객별 추천
- `recommend_similar_merchants` - 유사 가맹점 추천
- `search_documents` - RAG 문서 검색

### agent/intent.py
스트리밍 엔드포인트용 결정적 도구 실행:
- `detect_intent()` - 사용자 입력 인텐트 감지
- `run_deterministic_tools()` - 인텐트 기반 도구 자동 실행
- `set_last_context()` / `get_last_context()` - 컨텍스트 저장/조회
- `can_reuse_last_context()` - 요약 모드 판단

### agent/llm.py
- `build_langchain_messages()` - LangChain 메시지 빌더
- `get_llm()` - ChatOpenAI 인스턴스 생성
- `invoke_with_retry()` - 재시도 로직
- `pick_api_key()` - API 키 선택
- `chunk_text()` - 텍스트 청킹

### agent/runner.py
Tool Calling 방식의 에이전트 실행기:
- `run_agent()` - LLM이 직접 도구를 선택/호출
  1. LLM에 도구 바인딩 (`bind_tools`)
  2. 시스템 프롬프트에 도구 선택 가이드 포함
  3. LLM이 필요한 도구 자동 선택 및 호출
  4. 도구 결과를 바탕으로 최종 응답 생성
  5. 메모리 저장

### api/routes.py
모든 FastAPI 엔드포인트:

**인증**
- `POST /api/login` - 로그인 (메모리 초기화 포함)
- `GET /api/users` - 사용자 목록 (관리자)
- `POST /api/users` - 사용자 생성 (관리자)

**가맹점**
- `GET /api/merchants` - 전체 목록
- `GET /api/merchants/{id}` - 가맹점 현황
- `GET /api/merchants/{id}/metrics` - 가맹점 이력
- `POST /api/metrics/history/summary` - 이력 요약

**ML 분석**
- `POST /api/predict/revenue` - 매출 예측
- `POST /api/explain/revenue` - 매출 예측 설명
- `POST /api/detect/anomaly` - 이상 탐지
- `POST /api/explain/anomaly` - 이상 탐지 설명
- `POST /api/classify/growth` - 성장 분류
- `POST /api/explain/growth` - 성장 분류 설명

**업종**
- `GET /api/industries` - 업종 목록
- `POST /api/industry/compare` - 업종 비교

**RAG**
- `POST /api/rag/upload` - 문서 업로드
- `GET /api/rag/files` - 파일 목록
- `POST /api/rag/delete` - 파일 삭제 (관리자)
- `GET /api/rag/status` - RAG 상태 (Advanced Features 포함)
- `POST /api/rag/reload` - 인덱스 재빌드 (관리자)
- `POST /api/rag/search` - RAG 검색 (기본)
- `POST /api/rag/search/hybrid` - **Hybrid Search (BM25 + Vector + Reranking + KG)**

**OCR**
- `POST /api/ocr/extract` - 이미지에서 텍스트 추출 → RAG 저장 (EasyOCR)
- `GET /api/ocr/status` - OCR 시스템 상태

**GraphRAG**
- `POST /api/graphrag/build` - GraphRAG 지식 그래프 빌드 (LLM 기반)
- `POST /api/graphrag/search` - 그래프 기반 검색
- `GET /api/graphrag/status` - GraphRAG 상태 조회
- `POST /api/graphrag/clear` - GraphRAG 초기화

**에이전트**
- `POST /api/agent/chat` - 일반 요청
- `POST /api/agent/stream` - 스트리밍 응답
- `POST /api/agent/memory/clear` - 메모리 초기화

**Export**
- `GET /api/export/csv` - CSV 다운로드
- `GET /api/export/excel` - Excel 다운로드

**MLflow**
- `GET /api/mlflow/experiments` - MLflow 실험 목록 및 run 정보
- `GET /api/mlflow/models` - Model Registry 모델 목록 (모든 버전 포함)
- `POST /api/mlflow/models/select` - 모델 버전 선택 및 로드

**시스템**
- `GET /api/health` - 헬스체크
- `GET /api/ml/models` - ML 모델 정보

## Advanced RAG (검색 고도화)

### Hybrid Search (BM25 + Vector)
BM25 키워드 검색과 FAISS 벡터 검색을 결합하여 검색 품질 향상

| 검색 방식 | 특징 | 용도 |
|-----------|------|------|
| BM25 | 키워드 기반 | 정확한 단어 매칭 |
| Vector (FAISS) | 의미 기반 | 유사한 의미 검색 |
| Hybrid (RRF) | BM25 + Vector 융합 | 최적의 검색 결과 |

**Reciprocal Rank Fusion (RRF):**
```
RRF_score = Σ 1/(k + rank)
```

### Cross-Encoder Reranking
검색 결과를 Cross-Encoder 모델로 재정렬하여 관련성 향상

- 모델: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Query-Document 쌍의 관련성 점수 직접 계산
- 초기 검색 결과의 top-k를 재정렬

### Knowledge Graph (Simple)
문서에서 엔티티와 관계를 추출하여 Knowledge Graph 구축 (정규식 기반)

| 기능 | 설명 |
|------|------|
| Entity Extraction | 고유명사, 기술 용어 추출 (정규식) |
| Relation Extraction | 엔티티 간 관계 추출 (패턴) |
| Graph Search | 쿼리 관련 엔티티/관계 검색 |

### GraphRAG (LLM 기반)
Microsoft GraphRAG 아키텍처 기반 - **LLM으로 엔티티/관계 추출** + **NetworkX 그래프**

**작동 방식:**
1. RAG 문서 청크에서 LLM으로 엔티티/관계 추출 (GPT-4o-mini)
2. NetworkX로 지식 그래프 구축 (노드: 엔티티, 엣지: 관계)
3. Louvain 알고리즘으로 커뮤니티 탐지 (유사 개념 클러스터링)
4. 쿼리 시 관련 엔티티 + 이웃 노드 탐색으로 검색

**사용 시나리오:**
- 복잡한 도메인 지식 연결 (예: 금융 용어 간 관계)
- 엔티티 중심 검색 (예: "이 회사와 관련된 모든 기술")
- 문서 간 숨겨진 연결 발견

**GraphRAG API 사용법:**
```bash
# 1. 상태 확인
GET /api/graphrag/status
# → graphrag_ready: false이면 빌드 필요

# 2. 빌드 (관리자만, LLM 비용 발생)
POST /api/graphrag/build
{ "maxChunks": 20 }  # 처리할 청크 수 (비용 조절)

# 3. 검색
POST /api/graphrag/search
{
  "query": "금융 규제",
  "topK": 5,
  "includeNeighbors": true  # 이웃 노드 포함 여부
}
# → 관련 엔티티 + 관계 + 커뮤니티 정보 반환

# 4. 초기화
POST /api/graphrag/clear
```

**GraphRAG vs Simple KG:**
| 항목 | Simple KG | GraphRAG |
|------|-----------|----------|
| 추출 방식 | 정규식 | LLM (GPT-4) |
| 정확도 | 낮음 | 높음 |
| 비용 | 무료 | API 비용 발생 |
| 커뮤니티 탐지 | ❌ | ✅ |

### Hybrid Search API

```bash
POST /api/rag/search/hybrid
{
  "query": "가맹점 매출 분석",
  "topK": 5,
  "useReranking": true,
  "useKg": false
}
```

응답:
```json
{
  "status": "SUCCESS",
  "search_method": "hybrid",
  "reranked": true,
  "bm25_available": true,
  "reranker_available": true,
  "kg_available": true,
  "results": [
    {
      "title": "...",
      "content": "...",
      "bm25_score": 0.85,
      "vector_score": 0.72,
      "fusion_score": 0.031,
      "rerank_score": 0.89
    }
  ],
  "kg_entities": [...]
}
```

### 의존성

```bash
pip install rank-bm25          # BM25 키워드 검색
pip install sentence-transformers  # Cross-Encoder Reranking
pip install networkx           # GraphRAG 그래프 라이브러리
```

## ML 모델

| 모델 | 타입 | 목표 | 주요 지표 |
|------|------|------|----------|
| model_revenue.pkl | Random Forest Regressor | 다음 달 매출 예측 | R2: 0.81, MAPE: 21.27% |
| model_anomaly.pkl | Isolation Forest | 비정상 패턴 탐지 | 이상 비율: 5% |
| model_growth.pkl | Random Forest Classifier | 성장 유형 분류 | Accuracy: 82.81% |
| model_reco.pkl | SAR | 고객/유사 가맹점 추천 | Precision@10: 0.11, Recall@10: 0.63 |

## MLOps (MLflow)

### 모델 학습 및 실험 추적

```bash
# 모델 학습 (MLflow 추적)
python -m ml.train_models

# MLflow UI 실행
mlflow ui --port 5000
```

http://localhost:5000 에서 실험 결과 확인 가능

### MLflow 기능
- **실험 추적**: 파라미터, 메트릭 자동 기록
- **모델 레지스트리**: 모델 버전 관리 (v1, v2, v3... 선택 가능)
- **아티팩트 저장**: 모델 파일 및 관련 자료
- **API 연동**: 프론트엔드에서 실험/모델 조회 및 버전 선택

### 모델 타입
| 타입 | 설명 | 예시 |
|------|------|------|
| Registry | `mlflow.sklearn.log_model()` 사용, Model Registry 등록 | revenue, anomaly, growth |
| Artifact | `mlflow.log_artifact()` 사용, run 아티팩트로 저장 | recommendation (SAR) |

### 환경 변수
| 변수 | 기본값 | 설명 |
|------|--------|------|
| MLFLOW_TRACKING_URI | file:./mlruns | MLflow 저장 경로 |
| MLFLOW_EXPERIMENT_NAME | fintech-ml-models | 실험 이름 |

## 시작하기

### 의존성 설치

```bash
pip install fastapi uvicorn pandas numpy scikit-learn joblib
pip install langchain langchain-openai langchain-community langchain-text-splitters
pip install faiss-cpu pypdf
pip install mlflow  # MLOps
pip install recommenders # 추천 모델
pip install easyocr  # OCR (별도 설치 없이 바로 사용)
pip install rank-bm25  # Hybrid Search (BM25)
pip install sentence-transformers  # Cross-Encoder Reranking
pip install networkx  # GraphRAG (그래프 라이브러리)
```

### 서버 실행

```bash
cd backend
python main.py
# 또는
uvicorn main:app --reload --port 8000
```

### API 문서

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 인증

HTTP Basic Authentication

| 계정 | 비밀번호 | 권한 |
|------|---------|------|
| admin | admin123 | 관리자 |
| user | user123 | 사용자 |
| test | test | 사용자 |

## 설정값 (state.py)

| 설정 | 값 | 설명 |
|------|-----|------|
| RAG_MAX_DOC_CHARS | 200,000 | 문서 최대 문자수 |
| RAG_SNIPPET_CHARS | 1,200 | 검색 결과 스니펫 길이 |
| RAG_DEFAULT_TOPK | 3 | 기본 검색 결과 수 |
| RAG_MAX_TOPK | 10 | 최대 검색 결과 수 |
| MAX_MEMORY_TURNS | 5 | 대화 히스토리 턴 수 |
| LAST_CONTEXT_TTL_SEC | 600 | 컨텍스트 재사용 TTL (10분) |
| DEFAULT_TOPN | 10 | 기본 랭킹 수 |
| MAX_TOPN | 50 | 최대 랭킹 수 |

## 사용 예시

### RAG 문서 업로드 및 검색
```bash
# 1. 문서 업로드
curl -X POST http://localhost:8000/api/rag/upload \
  -u admin:admin123 \
  -F "file=@document.pdf"

# 2. 인덱스 재빌드 (BM25 + Simple KG 자동 빌드)
curl -X POST http://localhost:8000/api/rag/reload \
  -u admin:admin123 \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# 3. GraphRAG 빌드 (선택, LLM 비용 발생)
curl -X POST http://localhost:8000/api/graphrag/build \
  -u admin:admin123 \
  -H "Content-Type: application/json" \
  -d '{"maxChunks": 20}'

# 4. Hybrid Search
curl -X POST http://localhost:8000/api/rag/search/hybrid \
  -u admin:admin123 \
  -H "Content-Type: application/json" \
  -d '{"query": "가맹점 분석", "topK": 5, "useReranking": true}'
```

### AI 에이전트 스트리밍
```bash
curl -X POST http://localhost:8000/api/agent/stream \
  -u admin:admin123 \
  -H "Content-Type: application/json" \
  -d '{"message": "M0001 가맹점의 매출을 예측해줘"}' \
  --no-buffer
```

### MLflow 모델 버전 선택
```bash
# 1. 사용 가능한 모델 조회
curl http://localhost:8000/api/mlflow/models -u admin:admin123

# 2. 특정 버전 선택
curl -X POST http://localhost:8000/api/mlflow/models/select \
  -u admin:admin123 \
  -H "Content-Type: application/json" \
  -d '{"modelName": "revenue_model", "version": "2"}'
```

## FAQ

**Q: BM25/Simple KG가 "대기중"/"비활성"으로 표시됩니다.**
A: 라이브러리는 설치되었지만 인덱스가 빌드되지 않은 상태입니다. RAG 패널에서 "인덱스 재빌드" 버튼을 클릭하세요.

**Q: GraphRAG와 Simple KG의 차이는?**
A: Simple KG는 정규식 기반(무료), GraphRAG는 LLM 기반(유료)입니다. GraphRAG가 정확도가 높지만 API 비용이 발생합니다.

**Q: GraphRAG 빌드 시 비용은 얼마나 드나요?**
A: 청크 20개 기준 약 $0.05-0.10 (GPT-4o-mini 사용). maxChunks 파라미터로 조절 가능합니다.

**Q: RAG 인덱스 재빌드가 느립니다.**
A: 백그라운드에서 처리되므로 UI는 즉시 응답합니다. 상태는 `/api/rag/status`로 확인하세요.

**Q: ML 모델을 새 버전으로 교체하려면?**
A: MLflow UI에서 모델 등록 후 `/api/mlflow/models/select` 엔드포인트로 버전 선택하거나, .pkl 파일을 직접 교체 후 서버 재시작하세요.

**Q: OpenAI API 키는 어디에 설정하나요?**
A: 환경변수 `OPENAI_API_KEY` 또는 `state.py`의 `OPENAI_API_KEY`에 설정하세요.

## 로깅

- 로그 파일: `logs/backend.log`
- 로그 레벨: INFO
- 주요 이벤트: `APP_STARTUP`, `AGENT_START`, `RAG_READY`, `DATA_MODELS_READY`

---

**버전**: 3.3.0 (Advanced RAG: Hybrid Search + Reranking + Knowledge Graph + GraphRAG)
**최종 업데이트**: 2026-01-30
