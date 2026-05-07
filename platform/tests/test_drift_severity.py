from app.drift.severity import classify_severity

# Production thresholds — keep tests aligned with the settings defaults.
THRESHOLDS = dict(threshold_medium=0.1, threshold_high=0.25, threshold_critical=0.5)


def test_low_when_all_below_medium():
    assert classify_severity({"age": 0.05}, output_distribution_drift=0.02, **THRESHOLDS) == "low"


def test_medium_at_threshold():
    assert classify_severity({"age": 0.10}, output_distribution_drift=0.0, **THRESHOLDS) == "medium"


def test_high_at_threshold():
    assert classify_severity({"age": 0.25}, output_distribution_drift=0.0, **THRESHOLDS) == "high"


def test_critical_at_threshold():
    assert classify_severity({"age": 0.5}, output_distribution_drift=0.0, **THRESHOLDS) == "critical"


def test_output_drift_alone_can_trigger_critical():
    assert classify_severity({}, output_distribution_drift=0.6, **THRESHOLDS) == "critical"


def test_max_wins_across_features_and_output():
    psi = {"age": 0.05, "job": 0.30}  # job is 'high'
    assert classify_severity(psi, output_distribution_drift=0.01, **THRESHOLDS) == "high"


def test_empty_inputs_classify_as_low():
    assert classify_severity({}, output_distribution_drift=0.0, **THRESHOLDS) == "low"
