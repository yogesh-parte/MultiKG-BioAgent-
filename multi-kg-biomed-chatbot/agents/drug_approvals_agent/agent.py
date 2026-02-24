"""
Drug Approvals Agent (Stub)
---------------------------
Placeholder for a future FDA drug approvals KP.
Always skips gracefully when not in target_kgs or when endpoint is unavailable.
"""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

DRUG_APPROVALS_URL = "https://placeholder.drug-approvals.example/query"


def query_drug_approvals(tool_context: ToolContext) -> dict:
    """
    Stub: Query Drug Approvals KP for FDA-approved drug-disease associations.
    Endpoint not yet configured. Call with no arguments.
    """
    result = {
        "skipped": True,
        "reason": "Drug Approvals endpoint not configured",
        "placeholder_url": DRUG_APPROVALS_URL,
    }
    tool_context.state["drug_approvals_output"] = result
    return result


drug_approvals_agent = LlmAgent(
    name="drug_approvals_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Stub agent for FDA Drug Approvals KP (not yet configured).",
    instruction=(
        "You are a stub agent for the Drug Approvals KP.\n\n"
        "Call `query_drug_approvals` with NO arguments and return its response."
    ),
    tools=[query_drug_approvals],
    output_key="drug_approvals_output",
)
