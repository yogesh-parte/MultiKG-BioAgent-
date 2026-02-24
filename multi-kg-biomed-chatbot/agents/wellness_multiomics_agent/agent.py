"""
Wellness Multiomics Agent (Stub)
---------------------------------
Placeholder for a future Wellness Multiomics KP.
Always skips gracefully when not in target_kgs or when endpoint is unavailable.
"""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

WELLNESS_MULTIOMICS_URL = "https://placeholder.wellness-multiomics.example/query"


def query_wellness(tool_context: ToolContext) -> dict:
    """
    Stub: Query Wellness Multiomics KP for population-level multiomics associations.
    Endpoint not yet configured. Call with no arguments.
    """
    result = {
        "skipped": True,
        "reason": "Wellness Multiomics endpoint not configured",
        "placeholder_url": WELLNESS_MULTIOMICS_URL,
    }
    tool_context.state["wellness_output"] = result
    return result


wellness_multiomics_agent = LlmAgent(
    name="wellness_multiomics_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Stub agent for Wellness Multiomics KP (not yet configured).",
    instruction=(
        "You are a stub agent for the Wellness Multiomics KP.\n\n"
        "Call `query_wellness` with NO arguments and return its response."
    ),
    tools=[query_wellness],
    output_key="wellness_output",
)
