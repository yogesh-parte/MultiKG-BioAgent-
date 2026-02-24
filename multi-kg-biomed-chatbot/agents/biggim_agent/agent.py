"""
BigGIM Drug Response Agent
--------------------------
Queries the BigGIM Drug Response KP with a gene→drug TRAPI query.
Reads monarch_gene_curies from session state (set by monarch_agent after a multi-hop query).
Stores result as biggim_output.
"""

import requests
from typing import Any, Dict, List

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

BIGGIM_TRAPI_URL = (
    "https://api.bte.ncats.io/v1/smartapi/"
    "adf20dd6ff23dfe18e8e012bde686e31/query"
)


def build_trapi_gene_drug_query(gene_curies: List[str]) -> Dict[str, Any]:
    """
    Build a TRAPI query:
    Gene (n0) --[biolink:correlated_with]--> Drug (n1)

    Accepts a list of gene CURIEs for multi-gene queries.
    """
    return {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": gene_curies,
                        "categories": ["biolink:Gene"],
                    },
                    "n1": {
                        "categories": ["biolink:Drug"],
                    },
                },
                "edges": {
                    "e0": {
                        "subject": "n0",
                        "object": "n1",
                        "predicates": ["biolink:correlated_with"],
                    }
                },
            }
        }
    }


def query_biggim(tool_context: ToolContext) -> dict:
    """
    Query BigGIM Drug Response KP using gene CURIEs from Monarch output.
    Reads monarch_gene_curies from session state. Call with no arguments.
    """
    gene_curies = tool_context.state.get("monarch_gene_curies", [])
    if not gene_curies:
        result = {"skipped": True, "reason": "No gene CURIEs from Monarch — cannot query BigGIM"}
        tool_context.state["biggim_output"] = result
        return result

    trapi_query = build_trapi_gene_drug_query(gene_curies)

    try:
        resp = requests.post(BIGGIM_TRAPI_URL, json=trapi_query, timeout=60)
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        result = {
            "error": "BigGIM TRAPI request failed",
            "details": str(e),
            "endpoint": BIGGIM_TRAPI_URL,
            "gene_curies": gene_curies,
        }

    tool_context.state["biggim_output"] = result
    return result


biggim_agent = LlmAgent(
    name="biggim_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Queries BigGIM Drug Response KP for gene-drug correlations (multi-hop after Monarch).",
    instruction=(
        "You are a biomedical knowledge graph agent for BigGIM Drug Response KP.\n\n"
        "Your ONLY job: call the `query_biggim` tool with NO arguments. "
        "It will read gene CURIEs from session state and query BigGIM KP.\n\n"
        "Do NOT pass any arguments to `query_biggim`.\n"
        "Return the full tool response as your final output."
    ),
    tools=[query_biggim],
    output_key="biggim_status",
)
