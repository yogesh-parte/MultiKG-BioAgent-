"""
Simple TRAPI client for querying the Monarch KG.
This script:
1. Builds a TRAPI query graph.
2. Sends it to the Monarch KG TRAPI endpoint.
3. Prints out associated genes for a disease.

Run:
    python monarch_trapi_example.py

sample output:
=== Monarch KG Gene Results ===
Gene: SCN1A (HGNC:10585)
Gene: ….

"""

import asyncio
import httpx
from typing import Dict, Any

MONARCH_TRAPI_URL = (
    "https://robokop-automat.apps.renci.org/monarch-kg/"
    "reasoner_api_query_post_monarch-kg_trapi"
)


def build_trapi_query_graph(disease_curie: str) -> Dict[str, Any]:
    """
    Build a simple TRAPI query graph asking:
    Which genes are associated with this disease?
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
                    }
                },
                "edges": {
                    "e0": {
                        "subject": "n1",
                        "object": "n0",
                        "predicates": [
                            "biolink:gene_associated_with_condition"
                        ]
                    }
                }
            }
        }
    }


async def query_monarch_kg(trapi_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a TRAPI POST request to Monarch KG.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(MONARCH_TRAPI_URL, json=trapi_message)
        response.raise_for_status()
        return response.json()


def extract_gene_results(trapi_response: Dict[str, Any]) -> None:
    """
    Print subject genes from the TRAPI response message.
    """
    print("\n=== Monarch KG Gene Results ===")

    message = trapi_response.get("message", {})
    kg = message.get("knowledge_graph", {})
    nodes = kg.get("nodes", {})
    edges = kg.get("edges", {})

    if not edges:
        print("No gene associations found.")
        return

    for edge_id, edge in edges.items():
        subject = edge.get("subject")
        gene_node = nodes.get(subject, {})
        gene_name = gene_node.get("name", subject)
        print(f"Gene: {gene_name}  ({subject})")


async def main():
    # Example: Epilepsy = MONDO:0005151
    disease_curie = "MONDO:0005151"

    # Build TRAPI message
    trapi_query = build_trapi_query_graph(disease_curie)

    # Call Monarch KG
    response = await query_monarch_kg(trapi_query)

    # Extract and print genes
    extract_gene_results(response)


if __name__ == "__main__":
    asyncio.run(main())