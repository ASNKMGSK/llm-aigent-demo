# LLM & AI AGENT 핀테크 플랫폼 - Frontend

Next.js 기반 AI 에이전트 분석 플랫폼 프론트엔드

## 프로젝트 구조

```
nextjs/
├── pages/
│   ├── _app.js                 # Next.js App
│   ├── index.js                # 랜딩 페이지
│   ├── login.js                # 로그인
│   ├── app.js                  # 메인 앱
│   └── api/agent/stream.js     # SSE 프록시
│
├── components/
│   ├── Layout.js               # 레이아웃 (Sidebar + Topbar)
│   ├── Sidebar.js              # 사이드바 (가맹점 선택, 예시 질문)
│   ├── Topbar.js               # 상단바
│   ├── KpiCard.js              # KPI 카드
│   ├── Tabs.js                 # 탭
│   ├── EmptyState.js           # 빈 상태 UI
│   ├── SectionHeader.js        # 섹션 헤더
│   ├── Skeleton.js             # 로딩 스켈레톤
│   ├── ToastProvider.js        # 토스트 알림
│   └── panels/
│       ├── AgentPanel.js       # AI 에이전트 채팅
│       ├── AnalysisPanel.js    # ML 분석
│       ├── DashboardPanel.js   # 대시보드
│       ├── RagPanel.js         # RAG 문서 관리
│       ├── ModelsPanel.js      # 모델 정보
│       ├── UsersPanel.js       # 사용자 관리
│       ├── LogsPanel.js        # 로그 뷰어
│       └── SettingsPanel.js    # 설정
│
├── lib/
│   ├── api.js                  # API 호출 유틸리티
│   ├── cn.js                   # 클래스명 유틸리티
│   ├── progress.js             # 프로그레스바
│   ├── storage.js              # 로컬/세션 스토리지
│   └── utils.js                # 기타 유틸리티
│
├── styles/
│   └── globals.css             # 전역 스타일
│
├── next.config.js              # Next.js 설정
├── tailwind.config.js          # Tailwind 설정
└── package.json
```

## 기술 스택

| 라이브러리 | 버전 | 용도 |
|-----------|------|------|
| Next.js | 14 | React 프레임워크 |
| React | 18 | UI 라이브러리 |
| Tailwind CSS | 3.4 | 스타일링 |
| Framer Motion | 11 | 애니메이션 |
| Lucide React | - | 아이콘 |
| Plotly.js | 2.30 | 차트/시각화 |
| SWR | 2.2 | 데이터 페칭 |

## 주요 패널

| 패널 | 파일 | 설명 |
|------|------|------|
| Dashboard | DashboardPanel.js | 가맹점 KPI, 매출/거래량 차트 |
| Agent | AgentPanel.js | AI 에이전트 채팅 (스트리밍) |
| Analysis | AnalysisPanel.js | 매출 예측, 이상 탐지, 성장 분류 |
| RAG | RagPanel.js | 문서 업로드/검색/관리, Hybrid Search, Reranking, Simple KG, GraphRAG (PDF, OCR 지원) |
| Models | ModelsPanel.js | MLflow Model Registry, 모델 버전 선택 |
| Users | UsersPanel.js | 사용자 관리 (관리자) |
| Logs | LogsPanel.js | 활동 로그 |
| Settings | SettingsPanel.js | API 키, 모델 선택, 시스템 프롬프트 |

## 시작하기

### 설치
```bash
cd nextjs
npm install
```

### 환경 변수
`.env.local` 파일 생성:
```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
```

### 개발 서버
```bash
npm run dev
```
http://localhost:3000

### 프로덕션 빌드
```bash
npm run build
npm start
```

## 인증

HTTP Basic Authentication

| 계정 | 비밀번호 | 권한 |
|------|---------|------|
| admin | admin123 | 관리자 |
| user | user123 | 사용자 |
| test | test | 사용자 |

## API 통신

### 기본 사용법 (lib/api.js)
```javascript
import { apiCall } from '@/lib/api';

// GET
const data = await apiCall({
  endpoint: '/api/merchants',
  method: 'GET',
  auth: { username, password },
});

// POST
const result = await apiCall({
  endpoint: '/api/agent/chat',
  method: 'POST',
  data: { message: 'Hello' },
  auth: { username, password },
});
```

### 주요 API 엔드포인트
```
GET  /api/merchants         # 가맹점 목록
POST /api/agent/chat        # AI 에이전트
POST /api/agent/stream      # 스트리밍 응답
POST /api/predict/revenue   # 매출 예측
POST /api/detect/anomaly    # 이상 탐지
POST /api/classify/growth   # 성장 분류
POST /api/rag/upload        # 문서 업로드
GET  /api/rag/files         # 파일 목록
POST /api/rag/search        # RAG 검색 (벡터)
POST /api/rag/search/hybrid # Hybrid Search (BM25 + 벡터 + Reranking)
POST /api/rag/simple-kg/extract # Simple KG 엔티티 추출
POST /api/graphrag/build    # GraphRAG 지식 그래프 구축
POST /api/graphrag/search   # GraphRAG 검색
GET  /api/graphrag/status   # GraphRAG 상태
POST /api/ocr/extract       # OCR 이미지 → 텍스트 추출
GET  /api/ocr/status        # OCR 시스템 상태
GET  /api/mlflow/experiments # MLflow 실험 목록
GET  /api/mlflow/models      # Model Registry 모델 (모든 버전)
POST /api/mlflow/models/select # 모델 버전 선택/로드
```

## 스토리지 키

| 키 | 용도 |
|-----|------|
| auth | 인증 정보 (세션) |
| settings | LLM 설정 |
| agent_messages | 채팅 히스토리 |
| activity_log | 활동 로그 |
| total_queries | 쿼리 카운트 |

## 사용자 권한

| 권한 | 접근 가능 기능 |
|------|---------------|
| 관리자 | 모든 기능, RAG 업로드/삭제, 사용자 관리, 시스템 설정 |
| 사용자 | AI 에이전트, 대시보드, 분석 |

## 디자인 시스템

### 색상
| 용도 | 색상 |
|------|------|
| Primary | #111827 (다크 그레이) |
| Background | #f8fafc (밝은 그레이) |
| Border | #e2e8f0 |
| Text | #0f172a |

### 스타일
- 둥근 모서리: `rounded-3xl`, `rounded-2xl`
- 그림자: `shadow-sm`, `shadow-md`
- 백드롭 블러: `backdrop-blur`
- 애니메이션: Framer Motion

## 반응형

| 브레이크포인트 | 크기 | 레이아웃 |
|--------------|------|---------|
| xl | 1280px+ | 사이드바 고정 |
| lg | 1024px | 사이드바 토글 |
| sm | 640px | 모바일 최적화 |

## OCR 이미지 업로드 (RagPanel)

RAG 패널에서 이미지 파일을 업로드하면 OCR로 텍스트를 추출하여 RAG에 저장합니다.

### 기능
- **이미지 업로드**: JPG, PNG, BMP, TIFF, GIF, WEBP 지원
- **OCR 추출**: EasyOCR 기반 한국어/영어 텍스트 인식
- **RAG 연동**: 추출된 텍스트가 자동으로 RAG 문서로 저장
- **결과 미리보기**: 추출된 텍스트 내용 확인

### 사용 예시
1. RAG 패널에서 "OCR 이미지 업로드" 섹션 확인
2. 이미지 파일 선택 (영수증, 문서, 스캔 이미지 등)
3. "OCR 추출 → RAG 저장" 버튼 클릭
4. 추출된 텍스트가 RAG에 저장되어 검색 가능

---

## MLflow Model Registry (ModelsPanel)

### 기능
- **모델 목록 조회**: Model Registry에 등록된 모든 모델 표시
- **버전 선택**: 각 모델의 이전 버전 (v1, v2, v3...) 선택 가능
- **모델 로드**: 선택한 버전을 백엔드에 로드하여 분석에 사용
- **스테이지 표시**: Production, Staging, None 상태 표시
- **Artifact 모델**: Model Registry 외 아티팩트 기반 모델 (SAR 추천 모델) 표시

### 모델 타입
| 타입 | 뱃지 | 설명 |
|------|------|------|
| Registry | - | sklearn 모델 (revenue, anomaly, growth) |
| Artifact | 🟣 Artifact | 비-sklearn 모델 (recommendation/SAR) |

---

**버전**: 3.3.0
**최종 업데이트**: 2026-01-30
