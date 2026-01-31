# LLM & AI AGENT 핀테크 플랫폼

FastAPI 백엔드 + Next.js 프론트엔드 기반 AI 에이전트 분석 플랫폼

## 프로젝트 소개

가맹점 데이터를 분석하고 인사이트를 제공하는 AI 기반 핀테크 플랫폼입니다. 자연어로 질문하면 AI 에이전트가 적절한 도구를 선택하여 데이터를 조회하고 분석 결과를 제공합니다.

```
외부 웹앱 접속링크 : https://ernesto-unescalloped-pseudobiographically.ngrok-free.dev
```

### 핵심 기능

| 기능 | 설명 |
|------|------|
| **AI 에이전트** | LangChain Tool Calling 기반 자연어 질의 → 12개 도구 자동 선택 |
| **RAG 검색** | FAISS 벡터 DB로 문서 업로드/검색 (용어, 정책 등) |
| **Advanced RAG** | Hybrid Search (BM25+벡터), Cross-Encoder Reranking, Simple KG, GraphRAG |
| **매출 예측** | Random Forest 모델로 가맹점 매출 예측 |
| **이상 탐지** | Isolation Forest로 비정상 거래 패턴 감지 |
| **성장 분류** | 가맹점 성장 가능성 분류 (high/medium/low) |
| **추천 시스템** | SAR 알고리즘 기반 가맹점 추천 |
| **가맹점 분석** | 업종별/지역별 통계, Top N 랭킹, 트렌드 분석 |
| **OCR** | EasyOCR 기반 이미지 텍스트 추출 → RAG 연동 (한국어/영어) |
| **MLOps** | MLflow 기반 실험 추적, 모델 버전 관리, UI에서 버전 선택 |

## 프로젝트 구조

```
project/
├── frontend/                   # Next.js 프론트엔드
│   ├── pages/
│   │   ├── _app.js
│   │   ├── index.js            # 메인 페이지
│   │   ├── login.js            # 로그인 페이지
│   │   ├── app.js              # 앱 페이지
│   │   └── api/agent/stream.js # SSE 프록시
│   ├── components/
│   │   ├── Layout.js           # 레이아웃
│   │   ├── Sidebar.js          # 사이드바
│   │   ├── Topbar.js           # 상단바
│   │   ├── KpiCard.js          # KPI 카드
│   │   └── panels/
│   │       ├── AgentPanel.js   # AI 에이전트 채팅
│   │       ├── AnalysisPanel.js # ML 분석
│   │       ├── DashboardPanel.js # 대시보드
│   │       ├── RagPanel.js     # RAG 문서 관리
│   │       ├── ModelsPanel.js  # 모델 정보
│   │       ├── UsersPanel.js   # 사용자 관리
│   │       ├── LogsPanel.js    # 로그 뷰어
│   │       └── SettingsPanel.js # 설정
│   ├── lib/                    # 유틸리티
│   └── styles/                 # CSS
│
└── backend 리팩토링 시작/       # FastAPI 백엔드 (리팩토링 완료)
    ├── main.py                 # 앱 진입점
    ├── state.py                # 전역 상태
    ├── core/                   # 핵심 유틸리티
    ├── ml/                     # ML 헬퍼
    ├── data/                   # 데이터 로딩
    ├── rag/                    # RAG 서비스
    ├── agent/                  # AI 에이전트
    ├── api/                    # API 라우트
    ├── *.csv, *.pkl            # 데이터/모델
    └── rag_docs/, rag_faiss/   # RAG 저장소
```

## 프론트엔드 (frontend)

### 기술 스택
- **Next.js 14** - React 프레임워크
- **Tailwind CSS** - 스타일링
- **SWR** - 데이터 페칭
- **Plotly.js** - 차트/시각화
- **Framer Motion** - 애니메이션
- **Lucide React** - 아이콘

### 주요 기능
| 패널 | 설명 |
|------|------|
| Dashboard | 가맹점 현황, KPI 카드, 차트 |
| Agent | AI 에이전트 채팅 (스트리밍) |
| Analysis | ML 분석 (매출 예측, 이상 탐지, 성장 분류) |
| RAG | 문서 업로드/검색/관리, Hybrid Search, Reranking, Simple KG, OCR 이미지 업로드 |
| Models | MLflow Model Registry, 모델 버전 선택 |
| Users | 사용자 관리 (관리자) |
| Logs | 로그 뷰어 |
| Settings | 설정 |

### 실행
```bash
cd frontend
npm install
npm run dev
```
http://localhost:3000

## 백엔드 (backend 리팩토링 시작)

### 기술 스택
- **FastAPI** - 웹 프레임워크
- **LangChain** - LLM 통합
- **OpenAI** - GPT API, 임베딩
- **FAISS** - 벡터 검색
- **scikit-learn** - ML 모델

### 모듈 구조
| 모듈 | 설명 |
|------|------|
| `main.py` | FastAPI 앱, CORS, 미들웨어, startup |
| `state.py` | 전역 상태 (설정, 캐시, 모델 참조) |
| `core/` | constants, memory, parsers, utils |
| `ml/` | ML 헬퍼 함수 |
| `data/` | 데이터/모델 로딩 |
| `rag/` | RAG 서비스 (FAISS) |
| `agent/` | tools, tool_schemas, intent, llm, runner (Tool Calling 방식) |
| `api/` | FastAPI 라우트 |

### ML 모델
| 모델 | 타입 | 목표 | 성능 |
|------|------|------|------|
| model_revenue.pkl | Random Forest | 매출 예측 | R2: 0.81 |
| model_anomaly.pkl | Isolation Forest | 이상 탐지 | 이상률: 5% |
| model_growth.pkl | Random Forest | 성장 분류 | Accuracy: 82.81% |
| model_reco.pkl | SAR | 추천 | Precision@10: 0.11 |

### 주요 API
```
POST /api/agent/chat        # AI 에이전트
POST /api/agent/stream      # 스트리밍 응답
POST /api/predict/revenue   # 매출 예측
POST /api/detect/anomaly    # 이상 탐지
POST /api/classify/growth   # 성장 분류
POST /api/rag/upload        # 문서 업로드
POST /api/rag/search        # RAG 검색 (벡터)
POST /api/rag/search/hybrid # Hybrid Search (BM25 + 벡터 + Reranking)
POST /api/rag/simple-kg/extract # Simple KG 엔티티 추출
POST /api/graphrag/build    # GraphRAG 지식 그래프 구축
POST /api/graphrag/search   # GraphRAG 검색
GET  /api/graphrag/status   # GraphRAG 상태
POST /api/ocr/extract       # OCR 이미지 → 텍스트 추출 → RAG 저장
GET  /api/merchants         # 가맹점 목록
GET  /api/mlflow/experiments # MLflow 실험 목록
GET  /api/mlflow/models     # Model Registry (모든 버전)
POST /api/mlflow/models/select # 모델 버전 선택/로드
```

### 실행
```bash
cd "backend 리팩토링 시작"
pip install -r requirements.txt
python main.py
```
http://localhost:8000

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

## 전체 실행

```bash
# 터미널 1: 백엔드
cd "backend 리팩토링 시작"
python main.py

# 터미널 2: 프론트엔드
cd frontend
npm run dev
```

- 프론트엔드: http://localhost:3000
- 백엔드 API: http://localhost:8000

## 의존성 설치

### 백엔드
```bash
pip install fastapi uvicorn pandas numpy scikit-learn joblib
pip install langchain langchain-openai langchain-community langchain-text-splitters
pip install faiss-cpu pypdf
pip install mlflow  # MLOps
pip install recommenders  # SAR 추천
pip install easyocr  # OCR
pip install rank-bm25 sentence-transformers  # Advanced RAG (Hybrid Search, Reranking)
pip install networkx  # GraphRAG
```

### 프론트엔드
```bash
npm install
```

---

**버전**: 3.3.0
**최종 업데이트**: 2026-01-30
