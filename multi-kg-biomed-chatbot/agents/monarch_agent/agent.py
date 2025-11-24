import os
import requests
from typing import Any, Dict, Optional
from google.adk.agents import Agent 

MONARCH_TRAPI_URL = os.getenv(
    "MONARCH_TRAPI_URL",
    "https://robokop-automat.apps.renci.org/monarch-kg/query",
)

def query_monarch_trapi(
    trapi_request: Dict[str, Any],
    subclass: bool = True,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    Call the Monarch-KG TRAPI endpoint with a TRAPI request and return the TRAPI response.

    Use this tool when:
    - The user has provided a TRAPI query (either a full TRAPI request or at least a `message.query_graph`)
    - You need to execute that query against Monarch KG and then reason over the returned `knowledge_graph` and `results`.

    Args:
        trapi_request:
            A dict in TRAPI 1.4 format expected by Monarch-KG's `/monarch-kg/query` endpoint.
            Minimum:
              {
                "message": {
                  "query_graph": { ... }
                }
              }
            Optional fields like `workflow` are allowed.
        subclass:
            If True, pass `subclass=true` so Monarch expands disease/phenotype subclasses.
            Set False only if the user explicitly disables subclass expansion.
        validate:
            If True, pass `validate=true` so Monarch runs TRAPI schema validation.

    Returns:
        A dict containing the full TRAPI response from Monarch-KG, including:
        - message.query_graph
        - message.knowledge_graph (nodes, edges)
        - message.results (node_bindings, edge_bindings, scores, etc.)

    The agent should typically:
      1) Inspect `message.results` and `message.knowledge_graph`
      2) Summarize the key entities/relations back to the user in natural language.
    """
    params = {}
    if subclass:
        params["subclass"] = "true"
    if validate:
        params["validate"] = "true"

    # If user only gave "message", wrap into full TRAPI request
    if "message" in trapi_request and "query_graph" in trapi_request["message"] and len(trapi_request) == 1:
        payload = trapi_request
    else:
        # Assume user already provided a full request; just pass it through
        payload = trapi_request

    try:
        resp = requests.post(MONARCH_TRAPI_URL, params=params, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        # Returning a dict is nicer for the LLM than raising a raw exception
        return {
            "error": "Monarch TRAPI request failed",
            "details": str(e),
            "endpoint": MONARCH_TRAPI_URL,
            "params": params,
        }

    # TRAPI response
    return resp.json()


root_agent = Agent(
    name="monarch_agent",
    model="gemini-2.0-flash",  # or your configured model
    instruction=(
        "You are a biomedical knowledge graph assistant for the Monarch KG.\n"
        "- When the user supplies a TRAPI query (or a query_graph), "
        "call the `query_monarch_trapi` tool with that JSON.\n"
        "- Then inspect `message.knowledge_graph` and `message.results` "
        "to answer the user's question in natural language.\n"
        "- If the user gives a natural-language question instead of TRAPI, "
        "first propose a TRAPI query graph, then call the tool."
    ),
    tools=[query_monarch_trapi],
)
