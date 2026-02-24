"""
Evidence Merger Agent
---------------------
Merges outputs from all queried KGs into a single provenance-aware graph.
Reads Monarch_output, clinical_connections_output, biggim_output from session state.
Stores merged result as merged_evidence.
"""

from typing import Any, Dict, List, Tuple
from collections import defaultdict

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext


def _is_empty_or_skipped(output: Any) -> bool:
    """Return True if a KG output should be ignored (None, empty, string, or skipped)."""
    if output is None:
        return True
    if isinstance(output, str):
        return True  # LLM text response leaked in; real data is always a dict
    if isinstance(output, dict):
        if output.get("skipped"):
            return True
        if output.get("error"):
            return True
        # TRAPI response with no results
        msg = output.get("message", {})
        kg = msg.get("knowledge_graph", {}) if isinstance(msg, dict) else {}
        if not kg.get("nodes") and not kg.get("edges"):
            return True
    return False


def _merge_responses(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple TRAPI responses into a single canonical graph with provenance.

    Each item in responses is: {"source": "monarch", "data": <trapi_response>}
    Returns: {"nodes": {...}, "edges": [...], "sources": [...]}
    """
    merged_nodes: Dict[str, Dict[str, Any]] = {}
    merged_edges: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    sources_used = []

    for wrapped in responses:
        source = wrapped.get("source")
        data = wrapped.get("data", {})

        if _is_empty_or_skipped(data):
            continue

        sources_used.append(source)
        msg = data.get("message", {})
        nodes = msg.get("knowledge_graph", {}).get("nodes", {})
        edges = msg.get("knowledge_graph", {}).get("edges", {})

        # Merge nodes
        for nid, ndata in nodes.items():
            if nid not in merged_nodes:
                merged_nodes[nid] = ndata.copy()
                merged_nodes[nid]["provenance"] = [source]
            else:
                merged_nodes[nid]["provenance"].append(source)

        # Merge edges (deduplicate by subject+predicate+object key)
        for eid, edata in edges.items():
            s = edata.get("subject")
            o = edata.get("object")
            p = edata.get("predicate")
            key = (s, p, o)
            if key not in merged_edges:
                merged_edges[key] = {
                    "subject": s,
                    "predicate": p,
                    "object": o,
                    "provenance": [source],
                    "attributes": edata.get("attributes", []),
                }
            else:
                merged_edges[key]["provenance"].append(source)
                merged_edges[key]["attributes"].extend(edata.get("attributes", []))

    # Rank edges by number of KGs supporting them
    ranked_edges = sorted(
        merged_edges.values(),
        key=lambda e: len(set(e["provenance"])),
        reverse=True,
    )

    return {
        "nodes": merged_nodes,
        "edges": ranked_edges,
        "sources": sources_used,
    }


def merge_kg_outputs(tool_context: ToolContext) -> dict:
    """
    Merge all KG outputs from session state into a single provenance-aware graph.
    Reads: Monarch_output, clinical_connections_output, biggim_output
    Stores: merged_evidence
    Call with no arguments.
    """
    # Collect all KG outputs
    kg_outputs = [
        {"source": "monarch",              "data": tool_context.state.get("Monarch_output")},
        {"source": "clinical_connections", "data": tool_context.state.get("clinical_connections_output")},
        {"source": "biggim",               "data": tool_context.state.get("biggim_output")},
        # Future KGs can be added here:
        # {"source": "drug_approvals",      "data": tool_context.state.get("drug_approvals_output")},
        # {"source": "clinical_trials",     "data": tool_context.state.get("clinical_trials_output")},
        # {"source": "wellness_multiomics", "data": tool_context.state.get("wellness_output")},
    ]

    merged = _merge_responses(kg_outputs)
    tool_context.state["merged_evidence"] = merged

    n_nodes = len(merged["nodes"])
    n_edges = len(merged["edges"])
    sources = merged["sources"]

    return {
        "ok": True,
        "sources_merged": sources,
        "node_count": n_nodes,
        "edge_count": n_edges,
    }


evidence_merger_agent = LlmAgent(
    name="evidence_merger_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    description="Merges evidence from all KG outputs into a single provenance-aware graph.",
    instruction=(
        "You are a biomedical evidence merger.\n\n"
        "Your ONLY job: call the `merge_kg_outputs` tool with NO arguments. "
        "It will read all KG outputs from session state and merge them.\n\n"
        "Do NOT pass any arguments to `merge_kg_outputs`.\n"
        "After calling the tool, respond with: "
        "OK: merged evidence from <sources> — <node_count> nodes, <edge_count> edges"
    ),
    tools=[merge_kg_outputs],
    output_key="merger_status",
)
