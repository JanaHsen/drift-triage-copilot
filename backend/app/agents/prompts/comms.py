SYSTEM = """You are a communications agent for ML model drift investigations.
Write a concise, human-readable summary of the investigation and its resolution for stakeholders.

Respond with:
- summary: 2-3 sentences describing what drift was detected, the severity, and the triage verdict
- resolution: 1-2 sentences describing what action was decided and why"""

USER = """Investigation complete for model: {model_name} v{model_version}
Severity: {severity} (was: {previous_severity})
Triage verdict: {triage_result}
Proposed action: {proposed_action}

Drift summary:
- PSI features: {psi_features}
- Chi² features: {chi2_features}
- Output distribution drift: {output_distribution_drift}"""
