"""
Simple TRAPI client for querying the Clinical Connections KP.
This script:
1. Builds a TRAPI query graph.
2. Sends it to the Clinical Connections TRAPI endpoint.
3. Prints the disease-gene-drug association edges.

Run:
    python clinical_connections_trapi_example.py
"""

import asyncio
import httpx
from typing import Dict, Any

CLINICAL_CONNECTIONS_URL = (
    "https://robokop-automat.apps.renci.org/clinical_connections/"
    "reasoner-api/query"
)


def build_trapi_disease_gene_drug_query(disease_curie: str) -> Dict[str, Any]:
    """
    Build a TRAPI query graph:
    disease → gene → drug
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
                        "predicates": [
                            "biolink:gene_associated_with_condition"
                        ]
                    },
                    "e1": {
                        "subject": "n2",
                        "object": "n1",
                        "predicates": [
                            "biolink:affects_expression_of"
                        ]
                    }
                }
            }
        }
    }


async def query_clinical_connections(trapi_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST the TRAPI message to Clinical Connections KP.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(CLINICAL_CONNECTIONS_URL, json=trapi_message)
        response.raise_for_status()
        return response.json()


def print_edges(response: Dict[str, Any]) -> None:
    """
    Print out key edges from the TRAPI response.
    """
    print("\n=== Clinical Connections Results ===")

    message = response.get("message", {})
    kg = message.get("knowledge_graph", {})
    nodes = kg.get("nodes", {})
    edges = kg.get("edges", {})

    if not edges:
        print("No associations found.")
        return

    for edge_id, edge in edges.items():
        subj = edge.get("subject")
        obj = edge.get("object")

        subj_name = nodes.get(subj, {}).get("name", subj)
        obj_name = nodes.get(obj, {}).get("name", obj)

        predicate = edge.get("predicate", "unknown")

        print(f"{subj_name} ({subj})  --[{predicate}]-->  {obj_name} ({obj})")


async def main():
    # Example: Epilepsy
    disease_curie = "MONDO:0005151"

    trapi_query = build_trapi_disease_gene_drug_query(disease_curie)
    response = await query_clinical_connections(trapi_query)

    print_edges(response)


if __name__ == "__main__":
    asyncio.run(main())