"""Map raw drift values to the severity enum used in the contract."""

from typing import Literal

SeverityLevel = Literal["low", "medium", "high", "critical"]


def classify_severity(
    psi_features: dict[str, float],
    output_distribution_drift: float,
    *,
    threshold_medium: float,
    threshold_high: float,
    threshold_critical: float,
) -> SeverityLevel:
    """
    Severity = highest PSI band hit by ANY feature OR by output drift.

    Standard PSI bands: <0.1 stable, 0.1-0.25 moderate, 0.25-0.5 significant, >0.5 severe.
    chi² is reported but NOT used for classification — its threshold depends on
    degrees of freedom and is feature-specific.
    """
    max_psi = max([output_distribution_drift] + list(psi_features.values()), default=0.0)

    if max_psi >= threshold_critical:
        return "critical"
    if max_psi >= threshold_high:
        return "high"
    if max_psi >= threshold_medium:
        return "medium"
    return "low"
