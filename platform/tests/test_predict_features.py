from app.ml.predict import engineer_features
from app.schemas.predict import PredictionRequest


def _sample_payload(**overrides):
    base = {
        "age": 41, "job": "blue-collar", "marital": "married",
        "education": "basic.9y", "default": "no", "housing": "yes", "loan": "no",
        "contact": "cellular", "month": "may", "day_of_week": "mon",
        "campaign": 1, "pdays": 999, "previous": 0, "poutcome": "nonexistent",
        "emp.var.rate": 1.1, "cons.price.idx": 93.994, "cons.conf.idx": -36.4,
        "euribor3m": 4.857, "nr.employed": 5191,
    }
    base.update(overrides)
    return PredictionRequest.model_validate(base)


def test_pdays_999_engineers_to_never_contacted():
    df = engineer_features(_sample_payload(pdays=999))
    assert int(df["was_contacted_before"].iloc[0]) == 0
    assert int(df["days_since_contact"].iloc[0]) == 0
    assert "pdays" not in df.columns  # raw column dropped


def test_pdays_real_value_preserves_count():
    df = engineer_features(_sample_payload(pdays=10))
    assert int(df["was_contacted_before"].iloc[0]) == 1
    assert int(df["days_since_contact"].iloc[0]) == 10


def test_dotted_column_names_are_restored():
    df = engineer_features(_sample_payload())
    for col in ("emp.var.rate", "cons.price.idx", "cons.conf.idx", "nr.employed"):
        assert col in df.columns, f"missing dotted column {col}"


def test_engineered_dataframe_is_single_row():
    df = engineer_features(_sample_payload())
    assert len(df) == 1
