"""PSI and chi² drift computation against frozen training reference stats."""

import numpy as np

# Smoothing floor — avoids log(0) when a bin is empty.
_EPSILON = 1e-4


def psi_numeric(
    actual_values: list[float],
    reference_bin_edges: list[float],
    reference_frequencies: list[float],
) -> float:
    """
    PSI = Σ (actual_pct - expected_pct) * ln(actual_pct / expected_pct).
    Bins actual values using the reference's frozen bin edges.
    """
    if not actual_values:
        return 0.0

    edges = np.asarray(reference_bin_edges, dtype=float)
    # Clip out-of-range values into the first/last bin instead of dropping them.
    clipped = np.clip(actual_values, edges[0], edges[-1])
    actual_counts, _ = np.histogram(clipped, bins=edges)
    actual_pct = actual_counts / max(len(actual_values), 1)
    expected_pct = np.asarray(reference_frequencies, dtype=float)

    # Smooth zeros so log doesn't blow up.
    actual_pct = np.where(actual_pct == 0, _EPSILON, actual_pct)
    expected_pct = np.where(expected_pct == 0, _EPSILON, expected_pct)

    return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))


def chi2_categorical(
    actual_values: list[str],
    reference_frequencies: dict[str, float],
) -> float:
    """
    χ² = Σ (observed - expected)² / expected.
    Uses the union of categories from both sides.
    """
    if not actual_values:
        return 0.0

    all_cats = set(reference_frequencies.keys()) | set(map(str, actual_values))
    n = len(actual_values)

    actual_counts: dict[str, int] = {cat: 0 for cat in all_cats}
    for v in actual_values:
        key = str(v)
        actual_counts[key] = actual_counts.get(key, 0) + 1

    chi2 = 0.0
    for cat in all_cats:
        observed = actual_counts.get(cat, 0)
        expected_pct = reference_frequencies.get(cat, _EPSILON)
        expected_count = max(expected_pct * n, _EPSILON)
        chi2 += (observed - expected_count) ** 2 / expected_count

    return chi2


def compute_drift(
    predictions_payloads: list[dict],
    predictions_probas: list[float],
    reference_stats: dict,
) -> dict:
    """
    Per-feature drift across the rolling window.
    Returns shape matching contracts.v1.webhooks.DriftSummary.
    """
    psi_features: dict[str, float] = {}
    chi2_features: dict[str, float] = {}

    # Numeric: requires bin_edges + frequencies in reference stats.
    for feature, ref in reference_stats.get("numeric", {}).items():
        if "bin_edges" not in ref or "frequencies" not in ref:
            continue
        values = [p[feature] for p in predictions_payloads if feature in p]
        psi_features[feature] = psi_numeric(values, ref["bin_edges"], ref["frequencies"])

    # Categorical: reference is {category: frequency}.
    for feature, ref_freq in reference_stats.get("categorical", {}).items():
        values = [str(p[feature]) for p in predictions_payloads if feature in p]
        chi2_features[feature] = chi2_categorical(values, ref_freq)

    # Output distribution drift — PSI on the predicted probabilities.
    output_drift = 0.0
    ref_output = reference_stats.get("output_distribution")
    if ref_output and "bin_edges" in ref_output and "frequencies" in ref_output:
        output_drift = psi_numeric(
            predictions_probas, ref_output["bin_edges"], ref_output["frequencies"]
        )

    return {
        "psi_features": psi_features,
        "chi2_features": chi2_features,
        "output_distribution_drift": output_drift,
    }
