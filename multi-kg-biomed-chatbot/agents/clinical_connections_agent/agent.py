"""
Clinical Connections Agent
--------------------------
Queries the Clinical Connections KP with a disease→gene→drug 3-hop TRAPI query.
Reads disease_curie from session state; stores result as clinical_connections_output.
"""

import requests
from typing import Any, Dict

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

CLINICAL_CONNECTIONS_URL = (
    "https://robokop-automat.apps.renci.org/clinical_connections/"
    "reasoner-api/query"
)


def build_trapi_disease_gene_drug_query(disease_curie: str) -> Dict[str, Any]:
    """
    Build a TRAPI query graph: disease → gene → drug
    """
    return {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": [disease_curie],
                        "categories": ["biolink:Disease"]
                    },
                    "n1": {
                        "categories": ["biolink:Gene"]
                    },
                    "n2": {
                        "categories": ["biolink:Drug"]
                    }
                },
                "edges": {
                    "e0": {
                        "subject": "n1",
                        "object": "n0",
                        "predicates": ["biolink:gene_associated_with_condition"]
                    },
                    "e1": {
                        "subject": "n2",
                        "object": "n1",
                        "predicates": ["biolink:affects_expression_of"]
                    }
                }
            }
        }
    }


def query_clinical_connections(tool_context: ToolContext) -> dict:
    """
    Query Clinical Connections KP with disease→gene→drug 3-hop query.
    Reads disease_curie from session state. Call with no arguments.
    """
    disease_curie = tool_context.state.get("disease_curie")
    if not disease_curie:
        return {"skipped": True, "reason": "No disease_curie in session state"}

    trapi_query = build_trapi_disease_gene_drug_query(disease_curie)

    try:
        resp = requests.post(CLINICAL_CONNECTIONS_URL, json=trapi_query, timeout=60)
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        result = {
            "error": "Clinical Connections TRAPI request failed",
            "details": str(e),
            "endpoint": CLINICAL_CONNECTIONS_URL,
        }

    tool_context.state["clinical_connections_output"] = result
    return result


clinical_connections_agent = LlmAgent(
    name="clinical_connections_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Queries Clinical Connections KP for disease-gene-drug associations.",
    instruction=(
        "You are a biomedical knowledge graph agent for Clinical Connections KP.\n\n"
        "Your ONLY job: call the `query_clinical_connections` tool with NO arguments. "
        "It will read the disease CURIE from session state and query Clinical Connections KP.\n\n"
        "Do NOT pass any arguments to `query_clinical_connections`.\n"
        "Return the full tool response as your final output."
    ),
    tools=[query_clinical_connections],
    output_key="cc_status",
)
