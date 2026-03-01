from typing import Any, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext


def make_kg_skip_guard(kg_name: str, tool_name: str):
    """
    Returns a before_tool_callback that skips if kg_name not in target_kgs.

    Usage:
        before_tool_callback=make_kg_skip_guard("biggim", "query_biggim")
    """
    def guard(
        tool: BaseTool,
        args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        if tool.name != tool_name:
            return None
        target_kgs = tool_context.state.get("target_kgs", [])
        if kg_name not in target_kgs:
            return {"skipped": True, "reason": f"{kg_name} not selected for this query"}
        return None
    return guard


def before_monarch_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> Optional[dict]:
    """
    Before-tool callback for monarch_agent.

    Runs before every tool call. Only acts on 'run_monarch_query'.
    Guards against:
      1. Missing trapi_query in session state
      2. trapi_query not being a dict
      3. Missing message.query_graph structure
    """
    if tool.name != "run_monarch_query":
        return None  # pass through all other tools unchanged

    trapi_query = tool_context.state.get("trapi_query")

    # Guard 1: trapi_query must exist
    if not trapi_query:
        return {
            "error": (
                "Cannot query Monarch: 'trapi_query' is missing from session state. "
                "Ensure nlp_trapi_agent ran successfully before this step."
            )
        }

    # Guard 2: trapi_query must be a dict
    if not isinstance(trapi_query, dict):
        return {
            "error": (
                f"Cannot query Monarch: 'trapi_query' must be a dict, "
                f"got {type(trapi_query).__name__}. "
                "This usually means nlp_trapi_agent stored LLM text instead of a structured dict."
            )
        }

    # Guard 3: message.query_graph must exist
    msg = trapi_query.get("message")
    if not isinstance(msg, dict) or not msg.get("query_graph"):
        return {
            "error": (
                "Cannot query Monarch: 'trapi_query' is missing 'message.query_graph'. "
                "The TRAPI query is malformed."
            )
        }

    return None  # all checks passed — allow tool to run
