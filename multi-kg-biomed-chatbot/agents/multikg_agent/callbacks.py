import logging
from typing import Any, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# Query types supported by Monarch KG
SUPPORTED_QUERY_TYPES = {"gene_disease", "phenotype_disease"}

MONARCH_TOOL_NAME = "run_monarch_query"


def validate_trapi_query(trapi_query: Any) -> Optional[dict]:
    """
    Validates the structure of a TRAPI query dict.

    Returns an error dict if invalid, or None if valid.
    Error dict includes an 'error_code' key for programmatic handling.
    """
    if not trapi_query:
        logger.warning("Validation failed [ERR_MISSING_TRAPI_QUERY]: trapi_query absent from state")
        return {
            "error_code": "ERR_MISSING_TRAPI_QUERY",
            "error": (
                "Cannot query Monarch: 'trapi_query' is missing from session state. "
                "Ensure nlp_trapi_agent ran successfully before this step."
            ),
        }

    if not isinstance(trapi_query, dict):
        logger.warning(
            "Validation failed [ERR_INVALID_TRAPI_TYPE]: expected dict, got %s",
            type(trapi_query).__name__,
        )
        return {
            "error_code": "ERR_INVALID_TRAPI_TYPE",
            "error": (
                f"Cannot query Monarch: 'trapi_query' must be a dict, "
                f"got {type(trapi_query).__name__}. "
                "This usually means nlp_trapi_agent stored LLM text instead of a structured dict."
            ),
        }

    msg = trapi_query.get("message")
    if not isinstance(msg, dict) or not msg.get("query_graph"):
        logger.warning("Validation failed [ERR_MISSING_QUERY_GRAPH]: message.query_graph absent")
        return {
            "error_code": "ERR_MISSING_QUERY_GRAPH",
            "error": (
                "Cannot query Monarch: 'trapi_query' is missing 'message.query_graph'. "
                "The TRAPI query is malformed."
            ),
        }

    return None


def validate_monarch_query(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
) -> Optional[dict]:
    """
    Before-tool callback for monarch_agent.

    Runs before every tool call. Only acts on 'run_monarch_query'.
    Guards against:
      1. Missing trapi_query in session state        [ERR_MISSING_TRAPI_QUERY]
      2. trapi_query not being a dict                [ERR_INVALID_TRAPI_TYPE]
      3. Missing message.query_graph structure       [ERR_MISSING_QUERY_GRAPH]
      4. Unsupported query type (e.g. drug_disease)  [ERR_UNSUPPORTED_QUERY_TYPE]
    """
    if tool.name != MONARCH_TOOL_NAME:
        return None  # pass through all other tools unchanged

    logger.debug("Running pre-tool validation for '%s'", MONARCH_TOOL_NAME)

    trapi_query = tool_context.state.get("trapi_query")

    # Guards 1-3: structural validation
    validation_error = validate_trapi_query(trapi_query)
    if validation_error:
        return validation_error

    # Guard 4: block unsupported query types
    query_type = tool_context.state.get("query_type", "gene_disease")
    if query_type not in SUPPORTED_QUERY_TYPES:
        logger.warning(
            "Validation failed [ERR_UNSUPPORTED_QUERY_TYPE]: query_type=%s not in %s",
            query_type,
            SUPPORTED_QUERY_TYPES,
        )
        return {
            "error_code": "ERR_UNSUPPORTED_QUERY_TYPE",
            "error": (
                f"Monarch KG does not support query type '{query_type}'. "
                "Monarch KG has no drug treatment data — the predicate 'biolink:treats' is unavailable. "
                "Please ask about genes or phenotypes associated with a disease instead. "
                "Example: 'Which genes are associated with epilepsy?'"
            ),
        }

    logger.debug("Pre-tool validation passed for '%s'", MONARCH_TOOL_NAME)
    return None  # all checks passed — allow tool to run
