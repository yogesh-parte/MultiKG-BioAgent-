"""
Clinical Trials Agent (Stub)
-----------------------------
Placeholder for a future Clinical Trials KP (ClinicalTrials.gov).
Always skips gracefully when not in target_kgs or when endpoint is unavailable.
"""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

CLINICAL_TRIALS_URL = "https://placeholder.clinical-trials.example/query"


def query_clinical_trials(tool_context: ToolContext) -> dict:
    """
    Stub: Query Clinical Trials KP for active/completed trial data.
    Endpoint not yet configured. Call with no arguments.
    """
    result = {
        "skipped": True,
        "reason": "Clinical Trials endpoint not configured",
        "placeholder_url": CLINICAL_TRIALS_URL,
    }
    tool_context.state["clinical_trials_output"] = result
    return result


clinical_trials_agent = LlmAgent(
    name="clinical_trials_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Stub agent for Clinical Trials KP (not yet configured).",
    instruction=(
        "You are a stub agent for the Clinical Trials KP.\n\n"
        "Call `query_clinical_trials` with NO arguments and return its response."
    ),
    tools=[query_clinical_trials],
    output_key="clinical_trials_output",
)
