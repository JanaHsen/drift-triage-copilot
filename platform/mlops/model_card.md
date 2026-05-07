# Model Card — bank-marketing-classifier (v0.1.0-week5)

## Intended use
Predict whether a Portuguese retail bank customer will subscribe to a term
deposit, given pre-call customer attributes, prior-campaign history, and the
macroeconomic context at the time of the call. Used to prioritize outbound
calling lists.

## Training data
UCI Bank Marketing (`bank-additional-full.csv`), 41,188 rows, ~11.27% positive.
Stratified 60/20/20 train/val/test split, `random_state=42`.
Engineered features: dropped `duration` (target leakage); split `pdays` into
`was_contacted_before` (flag) + `days_since_contact` (numeric).

## Architecture
Single sklearn `Pipeline`:
- `ColumnTransformer`: `StandardScaler` on 10 numeric columns,
  `OneHotEncoder(handle_unknown='ignore')` on 10 categorical columns.
- Classifier: GradientBoosting,
  `class_weight='balanced'`, `random_state=42`.
- 63 features after preprocessing.

## Operating threshold
0.340 — chosen on validation as the highest threshold meeting
recall ≥ 0.75 (week 5 day 2 rule). Stored separately from the pipeline as a
serving-side configuration value.

## Metrics
| Split | AUC | F1 | Precision | Recall |
|-------|-----|----|-----------|--------|
| Train | 0.8633 | 0.3906 | 0.2526 | 0.8606 |
| Val   | 0.8057   | 0.3423   | 0.2206   | 0.7640 |
| Test  | 0.8136  | 0.3558  | 0.2296  | 0.7899 |

## Known limits
- Class imbalance (~11% positive). Threshold-sensitive — default 0.5 is wrong for this model.
- `default=yes` has only n=3 in training; that one-hot column is effectively unused.
- `month` reflects the bank's calling-strategy volume-vs-quality trade-off, not pure seasonality.
- Macroeconomic features span the 2008 financial crisis; behavior under future regime shifts is uncertain.
- No drift detection inside the model itself; drift is monitored externally over a rolling window.

## Artifact
- SHA-256: `20afcf1b003f9434a7fafc2165ef84391701aa8441aaf28c304d5e8510190ea4`
- File:    `bank_marketing_classifier.joblib` (180057 bytes)

## Environment fingerprint
```json
{
  "python": "3.12.13",
  "platform": "Windows-11-10.0.26200-SP0",
  "sklearn": "1.8.0",
  "numpy": "2.4.4",
  "pandas": "2.3.3",
  "mlflow": "3.11.1",
  "captured_at": "2026-05-06T18:35:39.592801+00:00"
}
```
