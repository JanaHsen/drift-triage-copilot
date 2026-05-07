from typing import Literal, Union

import anthropic as anthropic_sdk
import openai as openai_sdk
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

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


def _is_transient_llm_error(exc: BaseException) -> bool:
    if isinstance(exc, (openai_sdk.RateLimitError, anthropic_sdk.RateLimitError)):
        return True
    if isinstance(exc, openai_sdk.APIStatusError) and exc.status_code >= 500:
        return True
    if isinstance(exc, anthropic_sdk.APIStatusError) and exc.status_code >= 500:
        return True
    return False


_llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_transient_llm_error),
    reraise=True,
)


@_llm_retry
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
            timeout=30.0,
        )
        return response.choices[0].message.parsed  # type: ignore[return-value]
    else:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=prompts.triage.SYSTEM,
            tools=[
                {
                    "name": "submit_triage",
                    "description": "Submit the triage verdict and reasoning",
                    "input_schema": TriageOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "submit_triage"},
            messages=[{"role": "user", "content": user_msg}],
            timeout=30.0,
        )
        tool_block = next(b for b in response.content if b.type == "tool_use")
        return TriageOutput.model_validate(tool_block.input)


@_llm_retry
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
            timeout=30.0,
        )
        return response.choices[0].message.parsed  # type: ignore[return-value]
    else:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=prompts.action.SYSTEM,
            tools=[
                {
                    "name": "submit_action",
                    "description": "Submit the recommended action and reasoning",
                    "input_schema": ActionOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "submit_action"},
            messages=[{"role": "user", "content": user_msg}],
            timeout=30.0,
        )
        tool_block = next(b for b in response.content if b.type == "tool_use")
        return ActionOutput.model_validate(tool_block.input)


@_llm_retry
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
            timeout=30.0,
        )
        return response.choices[0].message.parsed  # type: ignore[return-value]
    else:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=prompts.comms.SYSTEM,
            tools=[
                {
                    "name": "submit_comms",
                    "description": "Submit the investigation summary and resolution",
                    "input_schema": CommsOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": "submit_comms"},
            messages=[{"role": "user", "content": user_msg}],
            timeout=30.0,
        )
        tool_block = next(b for b in response.content if b.type == "tool_use")
        return CommsOutput.model_validate(tool_block.input)
