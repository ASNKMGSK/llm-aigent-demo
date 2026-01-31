"""
MLflow 실험 추적 및 모델 관리 유틸리티
"""
import os
from typing import Any, Dict, Optional
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

# MLflow 저장 경로 (로컬)
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "fintech-ml-models")


def init_mlflow() -> MlflowClient:
    """MLflow 초기화 및 클라이언트 반환"""
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # 실험 생성 또는 가져오기
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        mlflow.create_experiment(EXPERIMENT_NAME)
    mlflow.set_experiment(EXPERIMENT_NAME)

    return MlflowClient()


def start_run(run_name: str, tags: Optional[Dict[str, str]] = None) -> mlflow.ActiveRun:
    """새 MLflow run 시작"""
    return mlflow.start_run(run_name=run_name, tags=tags)


def log_params(params: Dict[str, Any]) -> None:
    """파라미터 로깅"""
    for key, value in params.items():
        mlflow.log_param(key, value)


def log_metrics(metrics: Dict[str, float], step: Optional[int] = None) -> None:
    """메트릭 로깅"""
    for key, value in metrics.items():
        mlflow.log_metric(key, value, step=step)


def log_model_sklearn(model: Any, artifact_path: str, model_name: Optional[str] = None) -> None:
    """scikit-learn 모델 로깅 및 등록"""
    mlflow.sklearn.log_model(
        model,
        artifact_path=artifact_path,
        registered_model_name=model_name
    )


def log_artifact(local_path: str, artifact_path: Optional[str] = None) -> None:
    """아티팩트(파일) 로깅"""
    mlflow.log_artifact(local_path, artifact_path)


def end_run() -> None:
    """현재 run 종료"""
    mlflow.end_run()


def get_latest_model_version(model_name: str) -> Optional[str]:
    """등록된 모델의 최신 버전 조회"""
    client = MlflowClient()
    try:
        versions = client.get_latest_versions(model_name)
        if versions:
            return versions[0].version
    except Exception:
        pass
    return None


def load_model_from_registry(model_name: str, version: Optional[str] = None) -> Any:
    """모델 레지스트리에서 모델 로드"""
    if version is None:
        version = get_latest_model_version(model_name)

    model_uri = f"models:/{model_name}/{version}"
    return mlflow.sklearn.load_model(model_uri)


class MLflowExperiment:
    """MLflow 실험 추적을 위한 컨텍스트 매니저"""

    def __init__(self, run_name: str, tags: Optional[Dict[str, str]] = None):
        self.run_name = run_name
        self.tags = tags or {}
        self.run = None

    def __enter__(self):
        init_mlflow()
        self.run = mlflow.start_run(run_name=self.run_name, tags=self.tags)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        mlflow.end_run()
        return False

    def log_params(self, params: Dict[str, Any]) -> None:
        log_params(params)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        log_metrics(metrics, step)

    def log_model(self, model: Any, artifact_path: str, model_name: Optional[str] = None) -> None:
        log_model_sklearn(model, artifact_path, model_name)
