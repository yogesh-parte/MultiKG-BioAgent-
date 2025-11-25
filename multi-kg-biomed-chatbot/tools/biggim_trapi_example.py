"""
BigGIM Drug Response KP – TRAPI example.

SmartAPI docs:
    https://smart-api.info/ui/adf20dd6ff23dfe18e8e012bde686e31

see: https://docs.biothings.io/en/latest

This script:
1. Builds a TRAPI query asking which drugs have response relationships
   with a given gene (e.g., NCBIGene:23221).
2. Posts it to the BigGIM DrugResponse KP.
3. Prints gene–drug associations.

Run:
    python biggim_trapi_example.py
"""

import asyncio
from typing import Dict, Any

import httpx

BIGGIM_TRAPI_URL = (
    "https://api.bte.ncats.io/v1/smartapi/"
    "adf20dd6ff23dfe18e8e012bde686e31/query"
)


def build_trapi_gene_drug_query(gene_curie: str) -> Dict[str, Any]:
    """
    Build a basic TRAPI message:
    Gene (n0)  --[biolink:correlated_with]-->  Drug (n1)
    """
    return {
        "message": {
            "query_graph": {
                "nodes": {
                    "n0": {
                        "ids": [gene_curie],
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
                        "predicates": [
                            "biolink:correlated_with"
                        ],
                    }
                },
            }
        }
    }


async def query_biggim(trapi_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST a TRAPI message to the BigGIM Drug Response KP.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(BIGGIM_TRAPI_URL, json=trapi_message)
        response.raise_for_status()
        return response.json()


def print_gene_drug_edges(response: Dict[str, Any]) -> None:
    """
    Print gene–drug edges from TRAPI response.
    """
    print("\n=== BigGIM Drug Response KP Results ===")

    message = response.get("message", {})
    kg = message.get("knowledge_graph", {})
    nodes = kg.get("nodes", {})
    edges = kg.get("edges", {})

    if not edges:
        print("No gene–drug associations found.")
        return

    for edge_id, edge in edges.items():
        subj = edge.get("subject")
        obj = edge.get("object")
        predicate = edge.get("predicate", "biolink:related_to")

        subj_node = nodes.get(subj, {})
        obj_node = nodes.get(obj, {})

        subj_name = subj_node.get("name", subj)
        obj_name = obj_node.get("name", obj)

        print(f"{subj_name} ({subj}) --[{predicate}]--> {obj_name} ({obj})")


async def main():
    # Example gene (replace with your gene of interest)
    gene_curie = "NCBIGene:23221"

    trapi_query = build_trapi_gene_drug_query(gene_curie)
    response = await query_biggim(trapi_query)
    print_gene_drug_edges(response)


if __name__ == "__main__":
    asyncio.run(main())