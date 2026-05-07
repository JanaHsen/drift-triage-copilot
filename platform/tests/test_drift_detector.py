from app.drift.detector import chi2_categorical, compute_drift, psi_numeric


def test_psi_zero_when_distributions_match():
    edges = [0.0, 1.0, 2.0, 3.0]
    ref_freq = [1 / 3, 1 / 3, 1 / 3]
    # 30 values evenly distributed across the three bins.
    actual = [0.5] * 10 + [1.5] * 10 + [2.5] * 10

    psi = psi_numeric(actual, edges, ref_freq)
    assert psi < 0.01


def test_psi_high_when_distribution_shifts():
    edges = [0.0, 1.0, 2.0, 3.0]
    ref_freq = [1 / 3, 1 / 3, 1 / 3]
    # All mass in the first bin — large drift.
    actual = [0.5] * 30

    psi = psi_numeric(actual, edges, ref_freq)
    assert psi > 0.1


def test_psi_empty_input_returns_zero():
    assert psi_numeric([], [0.0, 1.0], [1.0]) == 0.0


def test_chi2_zero_when_distributions_match():
    ref_freq = {"a": 0.5, "b": 0.5}
    actual = ["a"] * 50 + ["b"] * 50

    chi2 = chi2_categorical(actual, ref_freq)
    assert chi2 < 1.0


def test_chi2_high_when_unseen_category_dominates():
    ref_freq = {"a": 1.0}
    actual = ["b"] * 100  # never seen during training

    chi2 = chi2_categorical(actual, ref_freq)
    assert chi2 > 100.0


def test_compute_drift_returns_contract_shape():
    reference = {
        "numeric": {
            "age": {
                "bin_edges": [0.0, 50.0, 100.0],
                "frequencies": [0.5, 0.5],
            }
        },
        "categorical": {"job": {"admin": 0.7, "blue-collar": 0.3}},
    }
    payloads = [{"age": 30, "job": "admin"}, {"age": 70, "job": "blue-collar"}]
    probas = [0.1, 0.2]

    drift = compute_drift(payloads, probas, reference)
    assert set(drift.keys()) == {"psi_features", "chi2_features", "output_distribution_drift"}
    assert "age" in drift["psi_features"]
    assert "job" in drift["chi2_features"]
