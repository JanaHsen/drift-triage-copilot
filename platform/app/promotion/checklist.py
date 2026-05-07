"""Day-4 promotion checklist. Each gate returns ChecklistResult; caller aggregates pass/fail."""

import json
import logging
from pathlib import Path

import mlflow
from mlflow.exceptions import MlflowException

from app.core.settings import settings
from contracts.v1.promote import ChecklistResult

logger = logging.getLogger(__name__)


def _client() -> mlflow.MlflowClient:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    return mlflow.MlflowClient()


def check_version_exists(name: str, version: str) -> ChecklistResult:
    """Candidate must exist in the registry."""
    try:
        mv = _client().get_model_version(name, version)
        return ChecklistResult(
            name="version_exists",
            passed=True,
            detail=f"v{version} found, current_stage={mv.current_stage}",
        )
    except MlflowException as exc:
        return ChecklistResult(name="version_exists", passed=False, detail=f"v{version} not found: {exc}")


def check_not_already_production(name: str, version: str) -> ChecklistResult:
    """Refuse to re-promote — silent no-op would mask bugs."""
    try:
        mv = _client().get_model_version(name, version)
        if mv.current_stage == "Production":
            return ChecklistResult(
                name="not_already_production",
                passed=False,
                detail=f"v{version} is already Production",
            )
        return ChecklistResult(
            name="not_already_production",
            passed=True,
            detail=f"current_stage={mv.current_stage}",
        )
    except MlflowException as exc:
        return ChecklistResult(name="not_already_production", passed=False, detail=str(exc))


def check_reference_stats_exist() -> ChecklistResult:
    """Drift detection breaks without these — block promotion."""
    path = settings.reference_stats_path
    if not path.is_file():
        return ChecklistResult(name="reference_stats_exist", passed=False, detail=f"missing at {path}")
    try:
        data = json.loads(path.read_text())
        if "numeric" not in data or "categorical" not in data:
            return ChecklistResult(
                name="reference_stats_exist",
                passed=False,
                detail="missing 'numeric' or 'categorical' keys",
            )
        return ChecklistResult(name="reference_stats_exist", passed=True, detail=f"{path.name} OK")
    except json.JSONDecodeError as exc:
        return ChecklistResult(name="reference_stats_exist", passed=False, detail=f"invalid JSON: {exc}")


def check_model_card_exists() -> ChecklistResult:
    """Audit trail requirement — every promoted version must have a card."""
    card_path = Path("mlops/model_card.md")
    if not card_path.is_file():
        return ChecklistResult(name="model_card_exists", passed=False, detail=f"missing at {card_path}")
    return ChecklistResult(name="model_card_exists", passed=True, detail=f"{card_path.name} OK")


def check_test_metrics(name: str, version: str, min_recall: float = 0.75) -> ChecklistResult:
    """Brief's recall>=0.75 rule. Looks for the metric under several conventional names."""
    try:
        client = _client()
        mv = client.get_model_version(name, version)
        run = client.get_run(mv.run_id)
        candidates = ["test_recall", "recall", "test_recall_pos", "recall_at_threshold"]
        for metric_name in candidates:
            if metric_name in run.data.metrics:
                value = run.data.metrics[metric_name]
                passed = value >= min_recall
                return ChecklistResult(
                    name="test_metrics_meet_threshold",
                    passed=passed,
                    detail=f"{metric_name}={value:.4f} {'>=' if passed else '<'} {min_recall}",
                )
        # Fail closed: promotion is destructive, so absent metrics block.
        return ChecklistResult(
            name="test_metrics_meet_threshold",
            passed=False,
            detail=f"no recall metric logged in run {mv.run_id} (looked for: {candidates})",
        )
    except MlflowException as exc:
        return ChecklistResult(name="test_metrics_meet_threshold", passed=False, detail=str(exc))


def run_checklist(model_name: str, target_version: str) -> list[ChecklistResult]:
    """Run all gates. Returns the full list — every check runs, even after a failure, so the audit shows everything."""
    return [
        check_version_exists(model_name, target_version),
        check_not_already_production(model_name, target_version),
        check_reference_stats_exist(),
        check_model_card_exists(),
        check_test_metrics(model_name, target_version),
    ]
