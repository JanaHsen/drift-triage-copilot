from typing import Literal, Union

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.agents import prompts
from app.agents.state import InvestigationState

LLMClient = Union[AsyncOpenAI, AsyncAnthropic]


class TriageOutput(BaseModel):
    verdict: Literal["real_drift", "no_drift"]
    reasoning: str


class ActionOutput(BaseModel):
    action: Literal["no_op", "replay", "retrain", "rollback"]
    reasoning: str


class CommsOutput(BaseModel):
    summary: str
    resolution: str


async def call_triage_llm(state: InvestigationState, client: LLMClient) -> TriageOutput:
    drift = state["drift_summary"]
    user_msg = prompts.triage.USER.format(
        model_name=state["model_name"],
        model_version=state["model_version"],
        previous_severity=state["previous_severity"] or "none",
        severity=state["severity"],
        psi_features=drift.get("psi_features", {}),
        chi2_features=drift.get("chi2_features", {}),
        output_distribution_drift=drift.get("output_distribution_drift", ""),
    )
    if isinstance(client, AsyncOpenAI):
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompts.triage.SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            response_format=TriageOutput,
        )
        return response.choices[0].message.parsed  # type: ignore[return-value]
    else:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=prompts.triage.SYSTEM,
            tools=[{
                "name": "submit_triage",
                "description": "Submit the triage verdict and reasoning",
                "input_schema": TriageOutput.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "submit_triage"},
            messages=[{"role": "user", "content": user_msg}],
        )
        tool_block = next(b for b in response.content if b.type == "tool_use")
        return TriageOutput.model_validate(tool_block.input)


async def call_action_llm(state: InvestigationState, client: LLMClient) -> ActionOutput:
    drift = state["drift_summary"]
    user_msg = prompts.action.USER.format(
        model_name=state["model_name"],
        model_version=state["model_version"],
        severity=state["severity"],
        psi_features=drift.get("psi_features", {}),
        chi2_features=drift.get("chi2_features", {}),
        output_distribution_drift=drift.get("output_distribution_drift", ""),
    )
    if isinstance(client, AsyncOpenAI):
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompts.action.SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            response_format=ActionOutput,
        )
        return response.choices[0].message.parsed  # type: ignore[return-value]
    else:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=prompts.action.SYSTEM,
            tools=[{
                "name": "submit_action",
                "description": "Submit the recommended action and reasoning",
                "input_schema": ActionOutput.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "submit_action"},
            messages=[{"role": "user", "content": user_msg}],
        )
        tool_block = next(b for b in response.content if b.type == "tool_use")
        return ActionOutput.model_validate(tool_block.input)


async def call_comms_llm(state: InvestigationState, client: LLMClient) -> CommsOutput:
    drift = state["drift_summary"]
    user_msg = prompts.comms.USER.format(
        model_name=state["model_name"],
        model_version=state["model_version"],
        severity=state["severity"],
        previous_severity=state["previous_severity"] or "none",
        triage_result=state["triage_result"] or "unknown",
        proposed_action=state["proposed_action"] or "none",
        psi_features=drift.get("psi_features", {}),
        chi2_features=drift.get("chi2_features", {}),
        output_distribution_drift=drift.get("output_distribution_drift", ""),
    )
    if isinstance(client, AsyncOpenAI):
        response = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompts.comms.SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            response_format=CommsOutput,
        )
        return response.choices[0].message.parsed  # type: ignore[return-value]
    else:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=prompts.comms.SYSTEM,
            tools=[{
                "name": "submit_comms",
                "description": "Submit the investigation summary and resolution",
                "input_schema": CommsOutput.model_json_schema(),
            }],
            tool_choice={"type": "tool", "name": "submit_comms"},
            messages=[{"role": "user", "content": user_msg}],
        )
        tool_block = next(b for b in response.content if b.type == "tool_use")
        return CommsOutput.model_validate(tool_block.input)
