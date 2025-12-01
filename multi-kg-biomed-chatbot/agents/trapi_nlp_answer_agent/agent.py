
from google.adk import Agent
import json

# ------------------------------
# TOOL 1 — Extract triples (Python)
# ------------------------------

def extract_trapi_triples(trapi_message: dict):
    """

# Explicitly register tools with the agent
try:
    agent.add_tool(extract_triples)
    agent.add_tool(summarize_graph)
    agent.add_tool(generate_answer)
except Exception:
    pass
    Pure Python triple extraction.
    No LLM. No cost. No rate limit.
    """
    message = trapi_message.get("message", {})
    kg = message.get("knowledge_graph", {})
    results = message.get("results", [])

    nodes = kg.get("nodes", {})
    edges = kg.get("edges", {})

    extracted = []
    edge_ids = set()

    # Find referenced edges
    for result in results:
        ebind = result.get("analyses", [{}])[0].get("edge_bindings", {})
        for v in ebind.values():
            for b in v:
                edge_ids.add(b["id"])

    for eid in edge_ids:
        if eid not in edges:
            continue
        e = edges[eid]
        subj = nodes.get(e["subject"], {}).get("name", e["subject"])
        obj = nodes.get(e["object"], {}).get("name", e["object"])
        pred = e.get("predicate", "")

        pubs, score, knowledge_level = [], None, ""

        for attr in e.get("attributes", []):
            aid = attr.get("attribute_type_id", "")
            val = attr.get("value")

            if "publication" in aid:
                if isinstance(val, list):
                    pubs.extend(val)
                else:
                    pubs.append(val)

            if "score" in aid or aid == "biolink:score":
                score = val

            if "knowledge_level" in aid:
                knowledge_level = val

        extracted.append({
            "subject": subj,
            "predicate": pred,
            "object": obj,
            "evidence": {
                "publications": pubs[:5],
                "knowledge_level": knowledge_level,
                "score": score,
            }
        })

    return {"triples": extracted}


# ------------------------------
# BUILD GOOGLE ADK AGENT
# ------------------------------

agent = Agent(
    name="trapi_nlp_answer_agent",
    model="gemini-2.0-flash",  
    description="Generates provenance-grounded natural language answers using TRAPI KG output."
)

# Register python tool
def extract_triples(trapi_message: dict) -> dict:
    """Extract triples from TRAPI message."""
    return extract_trapi_triples(trapi_message)


# ------------------------------
# TOOL 2 — Summarize triples (LLM)
# ------------------------------

def summarize_graph(triples: dict) -> dict:
    """
    Calls LLM to classify association types
    and infer disease families.
    """
    return agent.model.generate_content(f"""
    You are a biomedical KG summarizer.

    Group these triples:
    {json.dumps(triples, indent=2)}

    Into JSON with keys:
    {{
      "positive": [],
      "negative": [],
      "cooccurrence": [],
      "disease_families": {{}}
    }}

    Rules:
    - Use BioLink semantics.
    - "associated_with" = cooccurrence (weak)
    - "positively_correlated_with", "treats", "causes" → positive
    - "negatively_correlated_with", "contraindicated_for" → negative
    - Infer disease families (e.g. leukemia → hematologic cancers).
    """).text


# ------------------------------
# TOOL 3 — Generate final answer (LLM)
# ------------------------------

def generate_answer(question: str, summary: dict) -> str:
    """Generate final clinical/biomedical answer."""

    return agent.model.generate_content(f"""
    Create a clear biomedical answer to the question:
    "{question}"

    Use ONLY the following data:
    {json.dumps(summary, indent=2)}

    Requirements:
    - Distinguish positive / negative / co-occurrence
    - Mention disease family groupings
    - No hallucination
    - Use only TRAPI-provided facts
    """).text


# ------------------------------
# INFERENCE RUNNER
# ------------------------------

def run(question: str, trapi_message: dict):
    """
    Executes the 3-tool pipeline:
      1. extract triples
      2. summarize graph (LLM)
      3. generate final answer (LLM)
    """
    triples = extract_triples(trapi_message=trapi_message)
    summary = summarize_graph(triples=triples)
    answer = generate_answer(question=question, summary=json.loads(summary))

    return {
        "answer": answer,
        "triples": triples,
        "summary": json.loads(summary)
    }
