# ML Feature Columns
FEATURE_COLS_REG = [
    "txn_count",
    "unique_customers",
    "avg_order_value",
    "repeat_purchase_rate",
    "month_num",
    "industry_encoded",
    "region_encoded",
    "revenue_lag_1",
    "revenue_lag_2",
    "revenue_lag_3",
    "revenue_rolling_mean_3",
    "txn_rolling_mean_3",
]

FEATURE_COLS_ANOMALY = [
    "total_revenue",
    "txn_count",
    "avg_order_value",
    "repeat_purchase_rate",
    "ltv_cac_ratio",
]

FEATURE_COLS_CLF = [
    "total_revenue",
    "txn_count",
    "unique_customers",
    "avg_order_value",
    "repeat_purchase_rate",
    "ltv_cac_ratio",
    "revenue_growth_rate",
    "revenue_lag_1",
    "revenue_rolling_mean_3",
]

FEATURE_LABELS = {
    "txn_count": "거래건수",
    "unique_customers": "고객수",
    "avg_order_value": "객단가",
    "repeat_purchase_rate": "재구매율",
    "month_num": "월",
    "industry_encoded": "업종(인코딩)",
    "region_encoded": "지역(인코딩)",
    "revenue_lag_1": "1개월 전 매출",
    "revenue_lag_2": "2개월 전 매출",
    "revenue_lag_3": "3개월 전 매출",
    "revenue_rolling_mean_3": "3개월 매출 이동평균",
    "txn_rolling_mean_3": "3개월 거래건수 이동평균",
    "total_revenue": "매출",
    "ltv_cac_ratio": "LTV/CAC",
    "revenue_growth_rate": "매출 성장률",
}

# ML Model Metadata
ML_MODEL_INFO = {
    "model_revenue.pkl": {
        "name": "매출 예측 모델",
        "type": "Random Forest Regressor",
        "target": "다음 달 매출 예측",
        "features": ["거래건수", "고객수", "객단가", "재구매율", "월", "업종", "지역", "과거매출(1~3개월)", "이동평균"],
        "metrics": {
            "MAE": 736568,
            "RMSE": 1463523,
            "R2": 0.8114,
            "MAPE": 21.27,
        },
        "params": {},
        "data": {},
    },
    "model_anomaly.pkl": {
        "name": "이상 탐지 모델",
        "type": "Isolation Forest",
        "target": "비정상 거래 패턴 탐지",
        "features": ["매출", "거래건수", "객단가", "재구매율", "LTV/CAC"],
        "metrics": {
            "정상_비율(%)": 95.0,
            "이상_비율(%)": 5.0,
            "정상_건수": 912,
            "이상_건수": 48,
        },
        "params": {
            "contamination": 0.1,
            "n_estimators": 100,
        },
        "data": {},
    },
    "model_growth.pkl": {
        "name": "성장 분류 모델",
        "type": "Random Forest Classifier",
        "target": "성장 유형 분류 (급성장/안정/정체/하락)",
        "features": ["매출", "거래건수", "고객수", "객단가", "재구매율", "LTV/CAC", "성장률", "과거매출", "이동평균"],
        "metrics": {
            "Accuracy": 0.8281,
        },
        "params": {},
        "data": {},
    },
    "model_reco.pkl": {
        "name": "추천 모델",
        "type": "SAR (Microsoft Recommenders)",
        "target": "고객별 추천 / 유사 가맹점 추천",
        "features": [
            "고객 ID",
            "가맹점 ID",
            "구매횟수",
            "마지막 거래시점",
        ],
        "metrics": {
            "Precision@10": 0.1148,
            "Recall@10": 0.6338,
            "nDCG@10": 0.3699,
            "MAP@10": 0.2486,
        },
        "params": {
            "similarity_type": "jaccard",
            "time_decay_coefficient": 30,
            "timedecay_formula": True,
            "threshold": 1,
            "normalize": False,
            "col_user": "customer_id",
            "col_item": "merchant_id",
            "col_rating": "rating",
            "col_timestamp": "timestamp",
            "top_k_eval": 10,
        },
        "data": {
            "추천_학습_샘플": 55612,
            "추천_평가_샘플": 13907,
            "학습_고객_수": 9979,
            "학습_가맹점_수": 30,
        },
    },
}

# RAG Documents
RAG_DOCUMENTS = {
    "매출_성장률": {"title": "매출 성장률", "content": "전월 대비 당월 매출의 변화율 (%)입니다.", "keywords": ["매출", "성장률", "growth"]},
    "재구매율": {"title": "재구매율", "content": "2회 이상 구매한 고객의 비율입니다.", "keywords": ["재구매", "충성도", "repeat"]},
    "LTV_CAC": {"title": "LTV/CAC", "content": "고객 생애 가치 대비 획득 비용 비율입니다. 예시로 3:1 이상이면 건전합니다.", "keywords": ["LTV", "CAC"]},
    "이상탐지": {"title": "이상 탐지", "content": "Isolation Forest로 비정상 패턴을 탐지합니다. 점수는 모델 결정함수 기반입니다.", "keywords": ["이상", "anomaly"]},
    "성장유형": {"title": "성장 유형", "content": "급성장, 안정, 정체, 하락 4가지로 분류합니다. 신뢰도는 예측 확률 기반입니다.", "keywords": ["성장", "분류"]},
}

# Default System Prompt
DEFAULT_SYSTEM_PROMPT = """당신은 가맹점 데이터 분석 전문가입니다.

**응답 원칙**:
1. 제공된 내부 도구 결과(tool_results)를 우선적으로 활용하여 답변합니다.
2. RAG 검색 결과가 질문과 관련이 있다면 해당 정보를 참고합니다.
3. **단, RAG 결과가 없거나 질문과 무관한 경우, 일반 상식과 지식을 활용하여 답변합니다.**
4. 간단한 확인 질문("알아?", "뭐야?")에는 간단히 답변하고, 상세 분석 요청("분석해줘", "예측해줘")에는 심층 분석을 제공합니다.
5. 수치는 정확하게, 추측이나 단정은 하지 않습니다.

**응답 스타일**:
- 가맹점 ID 확인 질문: "네, M0002는 IT서비스 업종의 가맹점입니다. 상세 분석이 필요하시면 '분석해줘'라고 요청해주세요."
- 일반 상식 질문: RAG 결과 없어도 일반 지식으로 답변
- 상세 분석: 제공된 도구 결과를 바탕으로 구조화된 리포트 작성"""

# Memory Settings
MAX_MEMORY_TURNS = 5

# Ranking Settings
DEFAULT_TOPN = 10
MAX_TOPN = 50

# Summary Triggers
SUMMARY_TRIGGERS = [
    "요약", "정리", "요점", "핵심", "한줄", "한 줄", "간단히", "짧게", "요약해줘", "요약해 줘",
    "summary", "summarize", "tl;dr", "tldr"
]

# Recommendation Settings
RECO_COL_USER = "customer_id"
RECO_COL_ITEM = "merchant_id"
