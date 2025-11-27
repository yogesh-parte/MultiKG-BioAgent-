# agents/evidence_merger_agent.py
# TODO: A simplified version, need to work through

from typing import Dict, Any, List, Tuple
from collections import defaultdict

def merge_evidence(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
  """
  Merge multiple TRAPI responses into a single canonical graph.
  Assumes each 'data' is a standard TRAPI 'message'.
  """
  merged_nodes: Dict[str, Dict[str, Any]] = {}
  merged_edges: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

  for wrapped in responses:
    source = wrapped.get("source")
    msg = wrapped.get("data", {}).get("message", {})
    nodes = msg.get("knowledge_graph", {}).get("nodes", {})
    edges = msg.get("knowledge_graph", {}).get("edges", {})

    # merge nodes
    for nid, ndata in nodes.items():
      if nid not in merged_nodes:
        merged_nodes[nid] = ndata.copy()
        merged_nodes[nid]["provenance"] = [source]
      else:
        merged_nodes[nid]["provenance"].append(source)

    # merge edges
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

  # optional: rank edges by number of KPs supporting them
  ranked_edges = sorted(
    merged_edges.values(),
    key=lambda e: len(set(e["provenance"])),
    reverse=True,
  )

  return {
    "nodes": merged_nodes,
    "edges": ranked_edges,
  }