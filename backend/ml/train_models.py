import os
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, IsolationForest
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    classification_report,
    accuracy_score,
    f1_score,
)
import joblib
import warnings

warnings.filterwarnings("ignore")

# ========================================
# MLflow 설정
# ========================================
import mlflow
from mlflow.tracking import MlflowClient

# MLflow 저장 경로 (backend 폴더의 mlruns에 저장)
MLFLOW_TRACKING_URI = "file:./mlruns"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

EXPERIMENT_NAME = "fintech-ml-models"
experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
if experiment is None:
    mlflow.create_experiment(EXPERIMENT_NAME)
mlflow.set_experiment(EXPERIMENT_NAME)

print(f"MLflow Tracking URI: {MLFLOW_TRACKING_URI}")
print(f"MLflow Experiment: {EXPERIMENT_NAME}")

# ========================================
# numpy 호환 패치 (recommenders가 np.NaN을 참조하는 경우 대응)
# ========================================
if not hasattr(np, "NaN"):
    np.NaN = np.nan  # noqa: N816

try:
    from recommenders.models.sar.sar_singlenode import SARSingleNode
    from recommenders.evaluation.python_evaluation import (
        precision_at_k,
        recall_at_k,
        ndcg_at_k,
        map_at_k,
    )
except Exception as e:
    raise ImportError("recommenders 패키지가 필요합니다. pip install recommenders") from e

seed = 42
rng = np.random.default_rng(seed)

# ========================================
# 저장 경로 (요구사항: backend 폴더에 데이터/모델 저장)
# ========================================
BACKEND_DIR = Path(r"C:\Users\AKS\Desktop\project\backend 리팩토링 시작")
BACKEND_DIR.mkdir(parents=True, exist_ok=True)

# ========================================
# 1. 데이터 생성 (공통)
# ========================================
n_merchants = 30
n_customers = 10000
n_transactions = 100000

start_date = datetime(2023, 1, 1)
end_date = datetime(2025, 12, 31)

industries = ["음식점", "카페", "의류", "뷰티", "피트니스", "교육", "IT서비스", "배달"]
regions = ["서울", "경기", "부산", "대구", "인천"]

merchants = pd.DataFrame(
    {
        "merchant_id": [f"M{str(i).zfill(4)}" for i in range(1, n_merchants + 1)],
        "merchant_name": [f"가맹점_{i}" for i in range(1, n_merchants + 1)],
        "industry": rng.choice(industries, n_merchants, replace=True),
        "region": rng.choice(regions, n_merchants, replace=True),
        "growth_type": rng.choice(
            ["급성장", "안정", "정체", "하락"],
            n_merchants,
            replace=True,
            p=[0.15, 0.50, 0.25, 0.10],
        ),
    }
)

customers = pd.DataFrame(
    {
        "customer_id": [f"C{str(i).zfill(5)}" for i in range(1, n_customers + 1)],
        "segment": rng.choice(
            ["신규", "일반", "충성", "이탈위험"],
            n_customers,
            replace=True,
            p=[0.30, 0.40, 0.20, 0.10],
        ),
    }
)

customer_ids = customers["customer_id"].tolist()

# 월 리스트
month_periods = pd.period_range(start=start_date, end=end_date, freq="M")
month_strs = [str(p) for p in month_periods]

# merchant별 기본 성향(거래수/객단가) + 성장 타입별 트렌드
growth_map = dict(zip(merchants["merchant_id"], merchants["growth_type"]))

base_txn_mean = {}
base_aov = {}
loyal_weights = {}

for m_id in merchants["merchant_id"]:
    base_txn_mean[m_id] = float(rng.uniform(6.0, 18.0))
    base_aov[m_id] = float(rng.uniform(15000.0, 45000.0))

    loyal_set = set(rng.choice(customer_ids, size=max(30, int(n_customers * 0.15)), replace=False))
    w = np.ones(n_customers, dtype=float)
    for i, c in enumerate(customer_ids):
        if c in loyal_set:
            w[i] = 6.0
    loyal_weights[m_id] = w / w.sum()

# seasonality(월별)
seasonality = {}
for ms in month_strs:
    mnum = int(pd.to_datetime(ms).month)
    if mnum in [1, 2]:
        seasonality[ms] = 0.90
    elif mnum in [3, 4, 5]:
        seasonality[ms] = 1.00
    elif mnum in [6, 7, 8]:
        seasonality[ms] = 1.10
    elif mnum in [9, 10]:
        seasonality[ms] = 1.05
    else:
        seasonality[ms] = 1.15

# merchant-month weight 테이블
merchant_month_rows = []
for m_id in merchants["merchant_id"]:
    g = growth_map[m_id]
    for t_idx, ms in enumerate(month_strs):
        trend = 1.0
        if g == "급성장":
            trend = 1.0 + 0.03 * t_idx
        elif g == "하락":
            trend = max(0.25, 1.0 - 0.02 * t_idx)

        w = base_txn_mean[m_id] * trend * seasonality[ms]
        merchant_month_rows.append(
            {"merchant_id": m_id, "txn_month": ms, "t_idx": t_idx, "weight": w}
        )

merchant_month = pd.DataFrame(merchant_month_rows)

# anomaly 라벨 주입(merchant-month) - 데이터 다양성/검증용
anomaly_rate = 0.05
n_slots = len(merchant_month)
n_anomaly_slots = max(1, int(n_slots * anomaly_rate))
anomaly_slots_idx = rng.choice(np.arange(n_slots), size=n_anomaly_slots, replace=False)

merchant_month["anomaly_type"] = "정상"
anomaly_types = ["high_cancel", "revenue_spike", "aov_spike"]
merchant_month.loc[anomaly_slots_idx, "anomaly_type"] = rng.choice(
    anomaly_types, size=n_anomaly_slots, replace=True
)

# n_transactions 고정 배분 (multinomial)
weights = merchant_month["weight"].to_numpy(dtype=float)
weights = weights / weights.sum()
alloc = rng.multinomial(n_transactions, weights)
merchant_month["alloc_txn"] = alloc

# 트랜잭션 생성
transactions = []
txn_id_counter = 1

for row in tqdm(
    merchant_month.itertuples(index=False),
    total=len(merchant_month),
    desc="트랜잭션 생성(merchant-month 배분)",
):
    m_id = row.merchant_id
    ms = row.txn_month
    g = growth_map[m_id]
    anomaly_type = row.anomaly_type
    n_txn = int(row.alloc_txn)

    if n_txn <= 0:
        continue

    month_start = pd.to_datetime(ms + "-01")
    month_end = (month_start + pd.offsets.MonthEnd(1)).to_pydatetime()

    # growth_type별 aov 트렌드
    aov_mu = base_aov[m_id]
    if g == "급성장":
        aov_mu = aov_mu * (1.0 + 0.01 * row.t_idx)
    elif g == "하락":
        aov_mu = aov_mu * max(0.7, (1.0 - 0.005 * row.t_idx))

    # anomaly 반영
    success_p = 0.95
    cancel_p = 0.03
    fail_p = 0.02
    amount_mult = 1.0

    if anomaly_type == "high_cancel":
        success_p = 0.70
        cancel_p = 0.25
        fail_p = 0.05
        amount_mult = 1.0
    elif anomaly_type == "revenue_spike":
        success_p = 0.95
        cancel_p = 0.03
        fail_p = 0.02
        amount_mult = 2.5
    elif anomaly_type == "aov_spike":
        success_p = 0.90
        cancel_p = 0.07
        fail_p = 0.03
        amount_mult = 2.0

    # 금액 생성(lognormal)
    sigma = 0.45
    mu = np.log(max(1000.0, aov_mu)) - (sigma**2) / 2.0
    amounts = rng.lognormal(mean=mu, sigma=sigma, size=n_txn) * amount_mult
    amounts = np.clip(amounts, 1000.0, 500000.0).astype(int)

    # 날짜 분포
    days_in_month = (month_end - month_start.to_pydatetime()).days + 1
    day_offsets = rng.integers(0, days_in_month, size=n_txn)
    dates = [month_start.to_pydatetime() + timedelta(days=int(d)) for d in day_offsets]

    # 고객 선택(가맹점별 로열 가중치)
    cust_idx = rng.choice(
        np.arange(n_customers), size=n_txn, replace=True, p=loyal_weights[m_id]
    )
    custs = [customer_ids[i] for i in cust_idx]

    # 결제수단/상태
    payment_methods = rng.choice(
        ["카드", "간편결제", "계좌이체"], size=n_txn, replace=True, p=[0.60, 0.30, 0.10]
    )
    statuses = rng.choice(
        ["성공", "취소", "실패"], size=n_txn, replace=True, p=[success_p, cancel_p, fail_p]
    )

    for j in range(n_txn):
        transactions.append(
            {
                "txn_id": f"T{txn_id_counter:08d}",
                "merchant_id": m_id,
                "customer_id": custs[j],
                "txn_date": dates[j],
                "amount": int(amounts[j]),
                "payment_method": str(payment_methods[j]),
                "status": str(statuses[j]),
            }
        )
        txn_id_counter += 1

txn_df = pd.DataFrame(transactions)
txn_df["txn_date"] = pd.to_datetime(txn_df["txn_date"], errors="coerce")

# 성공 거래만 지표 산출
txn_success = txn_df[txn_df["status"] == "성공"].copy()
txn_success["txn_month"] = txn_success["txn_date"].dt.to_period("M").astype(str)

# 월별 지표 산출
monthly_revenue = (
    txn_success.groupby(["merchant_id", "txn_month"])
    .agg(
        total_revenue=("amount", "sum"),
        txn_count=("txn_id", "count"),
        unique_customers=("customer_id", "nunique"),
        avg_order_value=("amount", "mean"),
    )
    .reset_index()
)

monthly_revenue = monthly_revenue.sort_values(["merchant_id", "txn_month"])
monthly_revenue["prev_revenue"] = monthly_revenue.groupby("merchant_id")["total_revenue"].shift(1)
monthly_revenue["revenue_growth_rate"] = (
    (monthly_revenue["total_revenue"] - monthly_revenue["prev_revenue"])
    / monthly_revenue["prev_revenue"]
    * 100.0
).round(2)

# 반복구매율(월 내 동일 고객 2회 이상)
repeat_purchase = (
    txn_success.groupby(["merchant_id", "txn_month", "customer_id"])
    .size()
    .reset_index(name="purchase_count")
)
repeat_purchase["is_repeat"] = (repeat_purchase["purchase_count"] >= 2).astype(int)

repeat_rate = (
    repeat_purchase.groupby(["merchant_id", "txn_month"])
    .agg(total_customers=("customer_id", "count"), repeat_customers=("is_repeat", "sum"))
    .reset_index()
)
repeat_rate["repeat_purchase_rate"] = (
    repeat_rate["repeat_customers"] / repeat_rate["total_customers"] * 100.0
).round(2)

metrics = monthly_revenue.merge(
    repeat_rate[["merchant_id", "txn_month", "repeat_purchase_rate"]],
    on=["merchant_id", "txn_month"],
    how="left",
)
metrics = metrics.merge(
    merchants[["merchant_id", "merchant_name", "industry", "region", "growth_type"]],
    on="merchant_id",
    how="left",
)

# LTV/CAC
metrics["estimated_ltv"] = (
    metrics["avg_order_value"]
    * (12.0 * (1.0 + metrics["repeat_purchase_rate"].fillna(0.0) / 100.0))
).round(0)
metrics["cac_estimate"] = rng.integers(8000, 35000, len(metrics))
metrics["ltv_cac_ratio"] = (metrics["estimated_ltv"] / metrics["cac_estimate"]).round(2)

# anomaly 라벨(merchant-month)
metrics = metrics.merge(
    merchant_month[["merchant_id", "txn_month", "anomaly_type"]],
    on=["merchant_id", "txn_month"],
    how="left",
)
metrics["anomaly_type"] = metrics["anomaly_type"].fillna("정상")

# ========================================
# 2. 피처 엔지니어링
# ========================================
print("=" * 60)
print("피처 엔지니어링")
print("=" * 60)

metrics["txn_month_dt"] = pd.to_datetime(metrics["txn_month"], errors="coerce")
metrics["month_num"] = metrics["txn_month_dt"].dt.month
metrics["year"] = metrics["txn_month_dt"].dt.year

for lag in [1, 2, 3]:
    metrics[f"revenue_lag_{lag}"] = metrics.groupby("merchant_id")["total_revenue"].shift(lag)

metrics["revenue_rolling_mean_3"] = metrics.groupby("merchant_id")["total_revenue"].transform(
    lambda x: x.rolling(3, min_periods=1).mean()
)
metrics["txn_rolling_mean_3"] = metrics.groupby("merchant_id")["txn_count"].transform(
    lambda x: x.rolling(3, min_periods=1).mean()
)

le_industry = LabelEncoder()
le_region = LabelEncoder()
le_growth = LabelEncoder()

metrics["industry_encoded"] = le_industry.fit_transform(metrics["industry"])
metrics["region_encoded"] = le_region.fit_transform(metrics["region"])
metrics["growth_encoded"] = le_growth.fit_transform(metrics["growth_type"])

# 다음 달 매출 타깃
metrics["target_revenue_next"] = metrics.groupby("merchant_id")["total_revenue"].shift(-1)

# lag/target 때문에 NaN 발생 -> 제거(학습용)
metrics_clean = metrics.dropna().copy()
metrics_clean = metrics_clean.sort_values(["merchant_id", "txn_month_dt"]).reset_index(drop=True)

print("피처 엔지니어링 완료:", len(metrics_clean), "건")
print("주입 anomaly(merchant-month):", int((merchant_month["anomaly_type"] != "정상").sum()), "개 슬롯")
print("지표에 매칭된 anomaly(month):", int((metrics_clean["anomaly_type"] != "정상").sum()), "건")

# ========================================
# 3. 모델 1: 매출 예측 (RandomForest Regressor) - MLflow 추적
# ========================================
print("\n" + "=" * 60)
print("모델 1: 매출 예측 (RandomForest Regressor) - 다음 달 매출")
print("=" * 60)

feature_cols_reg = [
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

X_reg = metrics_clean[feature_cols_reg].copy()
y_reg = metrics_clean["target_revenue_next"].copy()

# time split: 마지막 20% 월 테스트
unique_months = sorted(metrics_clean["txn_month_dt"].dt.to_period("M").unique())
n_test_months = max(3, int(len(unique_months) * 0.2))
test_months = set(unique_months[-n_test_months:])

month_period = metrics_clean["txn_month_dt"].dt.to_period("M")
is_test = month_period.isin(test_months)

X_train_reg = X_reg[~is_test]
y_train_reg = y_reg[~is_test]
X_test_reg = X_reg[is_test]
y_test_reg = y_reg[is_test]

# MLflow 실험 추적 - 매출 예측
with mlflow.start_run(run_name="revenue_model"):
    mlflow.set_tag("model_type", "regression")
    mlflow.set_tag("target", "next_month_revenue")
    
    # 파라미터 로깅
    params = {"n_estimators": 200, "max_depth": 12, "random_state": seed}
    mlflow.log_params(params)
    mlflow.log_param("n_features", len(feature_cols_reg))
    mlflow.log_param("train_samples", len(X_train_reg))
    mlflow.log_param("test_samples", len(X_test_reg))
    
    rf_reg = RandomForestRegressor(**params, n_jobs=-1)
    rf_reg.fit(X_train_reg, y_train_reg)
    
    y_pred_reg = rf_reg.predict(X_test_reg)
    
    mae = mean_absolute_error(y_test_reg, y_pred_reg)
    rmse = float(np.sqrt(mean_squared_error(y_test_reg, y_pred_reg)))
    r2 = r2_score(y_test_reg, y_pred_reg)
    mape = float(np.mean(np.abs((y_test_reg - y_pred_reg) / np.clip(y_test_reg, 1.0, None))) * 100.0)
    
    # 메트릭 로깅
    mlflow.log_metrics({
        "mae": mae,
        "rmse": rmse,
        "r2_score": r2,
        "mape": mape,
    })
    
    # 모델 로깅
    mlflow.sklearn.log_model(rf_reg, "revenue_model", registered_model_name="fintech-revenue-model")
    
    print("MAE:", f"{mae:,.0f}", "원")
    print("RMSE:", f"{rmse:,.0f}", "원")
    print("R²:", f"{r2:.4f}")
    print("MAPE:", f"{mape:.2f}", "%")
    print(f"[MLflow] Run ID: {mlflow.active_run().info.run_id}")

# ========================================
# 4. 모델 2: 이상 탐지 (Isolation Forest) - MLflow 추적
# ========================================
print("\n" + "=" * 60)
print("모델 2: 이상 탐지 (Isolation Forest)")
print("=" * 60)

feature_cols_anomaly = [
    "total_revenue",
    "txn_count",
    "avg_order_value",
    "repeat_purchase_rate",
    "ltv_cac_ratio",
]

X_anomaly = metrics_clean[feature_cols_anomaly].copy()

scaler = StandardScaler()
X_anomaly_scaled = scaler.fit_transform(X_anomaly)

# MLflow 실험 추적 - 이상 탐지
with mlflow.start_run(run_name="anomaly_model"):
    mlflow.set_tag("model_type", "anomaly_detection")
    
    params = {"n_estimators": 200, "contamination": 0.05, "random_state": seed}
    mlflow.log_params(params)
    mlflow.log_param("n_features", len(feature_cols_anomaly))
    mlflow.log_param("n_samples", len(X_anomaly))
    
    iso_forest = IsolationForest(**params)
    anomaly_pred = iso_forest.fit_predict(X_anomaly_scaled)
    
    metrics_clean["anomaly_pred"] = anomaly_pred
    metrics_clean["anomaly_score"] = iso_forest.decision_function(X_anomaly_scaled)
    
    anomaly_count = int((anomaly_pred == -1).sum())
    normal_count = int((anomaly_pred == 1).sum())
    anomaly_ratio = anomaly_count / len(anomaly_pred)
    
    mlflow.log_metrics({
        "anomaly_count": anomaly_count,
        "normal_count": normal_count,
        "anomaly_ratio": anomaly_ratio,
    })
    
    mlflow.sklearn.log_model(iso_forest, "anomaly_model", registered_model_name="fintech-anomaly-model")
    
    print("정상 거래:", normal_count, "건", f"({normal_count/len(anomaly_pred)*100:.1f}%)")
    print("이상 거래:", anomaly_count, "건", f"({anomaly_count/len(anomaly_pred)*100:.1f}%)")
    print(f"[MLflow] Run ID: {mlflow.active_run().info.run_id}")

print("\n[이상 탐지된 샘플]")
anomaly_samples = (
    metrics_clean[metrics_clean["anomaly_pred"] == -1][
        [
            "merchant_id",
            "txn_month",
            "total_revenue",
            "txn_count",
            "avg_order_value",
            "repeat_purchase_rate",
            "ltv_cac_ratio",
            "anomaly_score",
            "anomaly_type",
        ]
    ]
    .sort_values("anomaly_score")
    .head(8)
)
print(anomaly_samples.to_string(index=False))

# ========================================
# 5. 모델 3: 추천 시스템 (Microsoft Recommenders - SAR) - MLflow 추적
# ========================================
print("\n" + "=" * 60)
print("모델 3: 추천 시스템 (Microsoft Recommenders - SAR)")
print("=" * 60)

interactions = (
    txn_success.groupby(["customer_id", "merchant_id"])
    .agg(
        interaction_count=("txn_id", "count"),
        last_ts=("txn_date", "max"),
    )
    .reset_index()
)

interactions["rating"] = interactions["interaction_count"].astype(float)
interactions["timestamp"] = pd.to_datetime(interactions["last_ts"], errors="coerce")

reco_df = interactions[["customer_id", "merchant_id", "rating", "timestamp"]].dropna().copy()

# timestamp를 epoch seconds로
reco_df["timestamp"] = (reco_df["timestamp"].astype("int64") // 10**9).astype("int64")

cutoff_ts = int(reco_df["timestamp"].quantile(0.8))
train_reco = reco_df[reco_df["timestamp"] < cutoff_ts].copy()
test_reco = reco_df[reco_df["timestamp"] >= cutoff_ts].copy()
test_reco = test_reco[test_reco["customer_id"].isin(train_reco["customer_id"])].copy()

print("추천 학습 샘플:", len(train_reco))
print("추천 평가 샘플:", len(test_reco))
print("학습 고객 수:", train_reco["customer_id"].nunique())
print("학습 가맹점 수:", train_reco["merchant_id"].nunique())

# MLflow 실험 추적 - 추천 (SAR 모델은 sklearn이 아니므로 artifact로 저장)
with mlflow.start_run(run_name="recommendation_model"):
    mlflow.set_tag("model_type", "recommendation")
    mlflow.set_tag("algorithm", "SAR")
    
    params = {
        "similarity_type": "jaccard",
        "time_decay_coefficient": 30,
        "timedecay_formula": True,
        "threshold": 1,
    }
    mlflow.log_params(params)
    mlflow.log_param("train_samples", len(train_reco))
    mlflow.log_param("test_samples", len(test_reco))
    mlflow.log_param("n_users", train_reco["customer_id"].nunique())
    mlflow.log_param("n_items", train_reco["merchant_id"].nunique())
    
    sar_model = SARSingleNode(
        col_user="customer_id",
        col_item="merchant_id",
        col_rating="rating",
        col_timestamp="timestamp",
        similarity_type="jaccard",
        time_decay_coefficient=30,
        timedecay_formula=True,
        threshold=1,
        normalize=False,
    )
    
    sar_model.fit(train_reco)
    
    k = 10
    test_users = test_reco[["customer_id"]].drop_duplicates().reset_index(drop=True)
    pred_reco = sar_model.recommend_k_items(test_users, top_k=k, sort_top_k=True, remove_seen=True)
    
    p_at_k = float(
        precision_at_k(
            test_reco, pred_reco,
            col_user="customer_id", col_item="merchant_id", col_prediction="prediction", k=k
        )
    )
    r_at_k = float(
        recall_at_k(
            test_reco, pred_reco,
            col_user="customer_id", col_item="merchant_id", col_prediction="prediction", k=k
        )
    )
    n_at_k = float(
        ndcg_at_k(
            test_reco, pred_reco,
            col_user="customer_id", col_item="merchant_id", col_prediction="prediction", k=k
        )
    )
    m_at_k = float(
        map_at_k(
            test_reco, pred_reco,
            col_user="customer_id", col_item="merchant_id", col_prediction="prediction", k=k
        )
    )
    
    mlflow.log_metrics({
        f"precision_at_{k}": p_at_k,
        f"recall_at_{k}": r_at_k,
        f"ndcg_at_{k}": n_at_k,
        f"map_at_{k}": m_at_k,
    })
    
    # SAR 모델을 pkl로 저장 후 아티팩트로 로깅
    reco_pkl_path = str(BACKEND_DIR / "model_reco.pkl")
    joblib.dump(sar_model, reco_pkl_path)
    mlflow.log_artifact(reco_pkl_path, artifact_path="model")
    
    print("Precision@K:", f"{p_at_k:.4f}", "K=", k)
    print("Recall@K:", f"{r_at_k:.4f}", "K=", k)
    print("nDCG@K:", f"{n_at_k:.4f}", "K=", k)
    print("MAP@K:", f"{m_at_k:.4f}", "K=", k)
    print(f"[MLflow] Run ID: {mlflow.active_run().info.run_id}")
    print(f"[MLflow] 추천 모델 아티팩트 저장됨: model/model_reco.pkl")

# ========================================
# 6. 모델 4: 성장 유형 분류 (RandomForest Classifier) - MLflow 추적
# ========================================
print("\n" + "=" * 60)
print("모델 4: 성장 유형 분류 (RandomForest Classifier)")
print("=" * 60)

feature_cols_clf = [
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

metrics_clf = metrics_clean.copy()
metrics_clf = metrics_clf[
    metrics_clf["revenue_growth_rate"].notna()
    & np.isfinite(metrics_clf["revenue_growth_rate"])
].copy()

X_clf = metrics_clf[feature_cols_clf].copy()
y_clf = metrics_clf["growth_encoded"].copy()

X_train_clf, X_test_clf, y_train_clf, y_test_clf = train_test_split(
    X_clf,
    y_clf,
    test_size=0.2,
    random_state=seed,
    stratify=y_clf,
)

# MLflow 실험 추적 - 성장 분류
with mlflow.start_run(run_name="growth_model"):
    mlflow.set_tag("model_type", "classification")
    mlflow.set_tag("target", "growth_type")
    
    params = {"n_estimators": 200, "max_depth": 12, "random_state": seed, "class_weight": "balanced"}
    mlflow.log_params(params)
    mlflow.log_param("n_features", len(feature_cols_clf))
    mlflow.log_param("train_samples", len(X_train_clf))
    mlflow.log_param("test_samples", len(X_test_clf))
    mlflow.log_param("n_classes", len(le_growth.classes_))
    
    rf_clf = RandomForestClassifier(**params, n_jobs=-1)
    rf_clf.fit(X_train_clf, y_train_clf)
    
    y_pred_clf = rf_clf.predict(X_test_clf)
    accuracy = accuracy_score(y_test_clf, y_pred_clf)
    f1_macro = f1_score(y_test_clf, y_pred_clf, average="macro")
    f1_weighted = f1_score(y_test_clf, y_pred_clf, average="weighted")
    
    mlflow.log_metrics({
        "accuracy": accuracy,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
    })
    
    mlflow.sklearn.log_model(rf_clf, "growth_model", registered_model_name="fintech-growth-model")
    
    print("Accuracy:", f"{accuracy:.4f}")
    print("F1 (macro):", f"{f1_macro:.4f}")
    print("F1 (weighted):", f"{f1_weighted:.4f}")
    print(f"[MLflow] Run ID: {mlflow.active_run().info.run_id}")

print("\n[Classification Report]")
target_names = le_growth.classes_
print(classification_report(y_test_clf, y_pred_clf, target_names=target_names))

# ========================================
# 7. 파일 저장 (backend 폴더에 저장)
# ========================================
print("\n" + "=" * 60)
print("파일 저장")
print("=" * 60)

merchants_out = BACKEND_DIR / "merchants.csv"
customers_out = BACKEND_DIR / "customers.csv"
transactions_out = BACKEND_DIR / "transactions.csv"
metrics_out = BACKEND_DIR / "metrics.csv"

txn_df_save = txn_df.copy()
txn_df_save["txn_date"] = pd.to_datetime(txn_df_save["txn_date"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

merchants.to_csv(merchants_out, index=False, encoding="utf-8-sig")
customers.to_csv(customers_out, index=False, encoding="utf-8-sig")
txn_df_save.to_csv(transactions_out, index=False, encoding="utf-8-sig")

metrics_save = metrics.copy()
metrics_save = metrics_save.drop(columns=["txn_month_dt"], errors="ignore")
metrics_save.to_csv(metrics_out, index=False, encoding="utf-8-sig")

# 모델/전처리 저장 (backend 호환 파일명 유지) - model_reco.pkl은 이미 위에서 저장됨
joblib.dump(rf_reg, BACKEND_DIR / "model_revenue.pkl")
joblib.dump(iso_forest, BACKEND_DIR / "model_anomaly.pkl")
joblib.dump(rf_clf, BACKEND_DIR / "model_growth.pkl")
joblib.dump(scaler, BACKEND_DIR / "scaler.pkl")
joblib.dump(le_industry, BACKEND_DIR / "le_industry.pkl")
joblib.dump(le_region, BACKEND_DIR / "le_region.pkl")
joblib.dump(le_growth, BACKEND_DIR / "le_growth.pkl")

print("저장 완료:")
print(str(merchants_out))
print(str(customers_out))
print(str(transactions_out))
print(str(metrics_out))
print(str(BACKEND_DIR / "model_revenue.pkl"))
print(str(BACKEND_DIR / "model_anomaly.pkl"))
print(str(BACKEND_DIR / "model_reco.pkl"))
print(str(BACKEND_DIR / "model_growth.pkl"))
print(str(BACKEND_DIR / "scaler.pkl"))
print(str(BACKEND_DIR / "le_industry.pkl"))
print(str(BACKEND_DIR / "le_region.pkl"))
print(str(BACKEND_DIR / "le_growth.pkl"))

# ========================================
# 8. MLflow 요약
# ========================================
print("\n" + "=" * 60)
print("MLflow 실험 추적 완료")
print("=" * 60)
print(f"Tracking URI: {MLFLOW_TRACKING_URI}")
print(f"Experiment: {EXPERIMENT_NAME}")
print("\n등록된 모델:")
print("  - fintech-revenue-model (sklearn)")
print("  - fintech-anomaly-model (sklearn)")
print("  - fintech-growth-model (sklearn)")
print("  - recommendation_model (artifact: model/model_reco.pkl)")
print("\nMLflow UI 실행: mlflow ui --port 5000")
print("브라우저에서 http://localhost:5000 접속")

# ========================================
# 9. 예측/이상/분류/추천 함수
# ========================================
def predict_revenue(merchant_data: dict) -> float:
    X = pd.DataFrame([merchant_data])[feature_cols_reg].astype(float)
    return float(rf_reg.predict(X)[0])

def detect_anomaly(merchant_data: dict) -> dict:
    X = pd.DataFrame([merchant_data])[feature_cols_anomaly].astype(float)
    X_scaled = scaler.transform(X)
    pred = int(iso_forest.predict(X_scaled)[0])
    score = float(iso_forest.decision_function(X_scaled)[0])
    return {"is_anomaly": pred == -1, "score": score}

def classify_growth(merchant_data: dict) -> dict:
    X = pd.DataFrame([merchant_data])[feature_cols_clf].astype(float)
    pred = int(rf_clf.predict(X)[0])
    proba = rf_clf.predict_proba(X)[0]
    classes = le_growth.classes_
    prob_dict = {str(classes[i]): float(proba[i]) for i in range(len(classes))}
    return {"growth_type": str(le_growth.inverse_transform([pred])[0]), "probabilities": prob_dict}

def recommend_merchants_for_customer(customer_id: str, top_k: int = 5) -> pd.DataFrame:
    # cold-start: 학습에 없는 고객이면 인기 가맹점 추천으로 폴백
    if getattr(sar_model, "user2index", None) is None or customer_id not in sar_model.user2index:
        pop = sar_model.get_popularity_based_topk(top_k=top_k, sort_top_k=True, items=True)
        out = pop.rename(columns={"prediction": "score"}).merge(
            merchants[["merchant_id", "merchant_name", "industry", "region"]],
            on="merchant_id",
            how="left",
        )
        return out

    user_df = pd.DataFrame({"customer_id": [customer_id]})
    recs = sar_model.recommend_k_items(user_df, top_k=top_k, sort_top_k=True, remove_seen=True)
    out = recs.rename(columns={"prediction": "score"}).merge(
        merchants[["merchant_id", "merchant_name", "industry", "region"]],
        on="merchant_id",
        how="left",
    )
    return out

def recommend_similar_merchants(seed_merchant_id: str, top_k: int = 5) -> pd.DataFrame:
    seed_df = pd.DataFrame({"merchant_id": [seed_merchant_id]})
    recs = sar_model.get_item_based_topk(seed_df, top_k=top_k, sort_top_k=True)
    out = recs.rename(columns={"prediction": "score"}).merge(
        merchants[["merchant_id", "merchant_name", "industry", "region"]],
        on="merchant_id",
        how="left",
    )
    return out

print("\n[예측/이상/분류/추천 함수 테스트]")
sample = metrics_clean.iloc[0].to_dict()
print("샘플 가맹점:", sample["merchant_id"], "월:", sample["txn_month"])
print("다음 달 매출 예측:", f"{predict_revenue(sample):,.0f}", "원", "(현재월 실제:", f"{int(sample['total_revenue']):,}", "원 )")
print("이상 탐지:", detect_anomaly(sample))
print("성장 분류:", classify_growth(sample))

sample_customer_id = train_reco["customer_id"].iloc[0]
print("\n샘플 고객:", sample_customer_id)
print("[추천 가맹점 Top5]")
print(recommend_merchants_for_customer(sample_customer_id, top_k=5).to_string(index=False))

sample_merchant_id = merchants["merchant_id"].iloc[0]
print("\n시드 가맹점:", sample_merchant_id)
print("[유사 가맹점 Top5]")
print(recommend_similar_merchants(sample_merchant_id, top_k=5).to_string(index=False))