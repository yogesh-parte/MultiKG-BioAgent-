"""
TRAPI NLP Answer Agent

Generates natural language answers grounded strictly in TRAPI knowledge graphs.

Pipeline:
  1. extract_trapi_triples()    - Pure Python extraction (no LLM)
  2. summarize_graph()          - LLM classifies associations
  3. generate_answer()          - LLM composes grounded NL answer

No hallucination—all facts extracted before LLM reasoning begins.
"""

import json
import os
import openai
from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

class _Response:
    def __init__(self, text: str):
        self.text = text

class _Model:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = openai.OpenAI()
        return self._client

    def generate_content(self, prompt: str):
        resp = self._get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return _Response(resp.choices[0].message.content)

MODEL = _Model()


# ============================================================================
# TOOL 1: Extract triples (Pure Python, No LLM)
# ============================================================================

def format_merged_evidence(merged_evidence: dict) -> dict:
    """
    Convert merged_evidence (from evidence_merger_agent) into the triples format
    that the downstream summarize/generate pipeline already consumes.

    merged_evidence schema: {"nodes": {...}, "edges": [...], "sources": [...]}
    Returns: {"triples": [...]} matching the output of extract_trapi_triples.
    """
    nodes = merged_evidence.get("nodes", {})
    edges = merged_evidence.get("edges", [])
    sources = merged_evidence.get("sources", [])

    extracted = []
    for edge in edges:
        subj_id = edge.get("subject", "")
        obj_id = edge.get("object", "")
        pred = edge.get("predicate", "")
        provenance = edge.get("provenance", [])

        subj_name = nodes.get(subj_id, {}).get("name", subj_id)
        obj_name = nodes.get(obj_id, {}).get("name", obj_id)

        # Flatten attributes for publications/score/knowledge_level
        pubs, score, knowledge_level = [], None, ""
        for attr in edge.get("attributes", []):
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
            "subject": subj_name,
            "predicate": pred,
            "object": obj_name,
            "evidence": {
                "publications": pubs[:5],
                "knowledge_level": knowledge_level,
                "score": score,
                "sources": provenance,
            }
        })

    return {"triples": extracted, "sources": sources}


def extract_trapi_triples(trapi_message: dict) -> dict:
    """
    Pure Python triple extraction.
    No LLM. No cost. No rate limit.
    """
    print("[TRAPI-NLP] [EXTRACT-A] Extracting triples from TRAPI message...")
    
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

    print(f"[TRAPI-NLP] [SUCCESS] Extracted {len(extracted)} triples")
    return {"triples": extracted}


# ============================================================================
# TOOL 2: Summarize triples (LLM)
# ============================================================================

def summarize_graph(triples: dict) -> dict:
    """
    Calls LLM to classify association types and infer disease families.
    """
    print("[TRAPI-NLP] [SUMMARIZE-B] Summarizing graph with LLM (classification)...")
    
    if not MODEL:
        print("[TRAPI-NLP] [WARNING] LLM not available, returning empty summary")
        return {
            "positive": [],
            "negative": [],
            "cooccurrence": [],
            "disease_families": {}
        }
    
    prompt = f"""
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
- "gene_associated_with_condition" = positive
- "negatively_correlated_with", "contraindicated_for" → negative
- Infer disease families (e.g. leukemia → hematologic cancers).

Return ONLY valid JSON. Start with {{ and end with }}.
"""
    
    try:
        resp = MODEL.generate_content(prompt)
        text = resp.text.strip()
        
        # Extract JSON if wrapped in markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        result = json.loads(text)
        print("[TRAPI-NLP] [SUCCESS] Summary classified")
        return result
    except Exception as e:
        print(f"[TRAPI-NLP] [WARNING] Error in summarization: {str(e)}")
        return {
            "positive": [],
            "negative": [],
            "cooccurrence": [],
            "disease_families": {}
        }


# ============================================================================
# TOOL 3: Generate final answer (LLM)
# ============================================================================

def generate_answer(question: str, summary: dict) -> str:
    """Generate final clinical/biomedical answer."""
    
    print("[TRAPI-NLP] [GENERATE-C] Generating natural language answer...")
    
    if not MODEL:
        print("[TRAPI-NLP] [WARNING] LLM not available")
        return "LLM not available"

    prompt = f"""
Create a clear biomedical answer to the question:
"{question}"

Use ONLY the following data:
{json.dumps(summary, indent=2)}

Requirements:
- Distinguish positive / negative / co-occurrence
- Mention disease family groupings
- No hallucination
- Use only TRAPI-provided facts
"""
    
    try:
        resp = MODEL.generate_content(prompt)
        answer = resp.text.strip()
        print("[TRAPI-NLP] [SUCCESS] Answer generated")
        return answer
    except Exception as e:
        print(f"[TRAPI-NLP] [WARNING] Error generating answer: {str(e)}")
        return f"Error: {str(e)}"


# ============================================================================
# NO-ARG STATE WRAPPER (used by explain_agent as a tool)
# ============================================================================

def run_answer_pipeline(tool_context: ToolContext) -> dict:
    """
    Run the full answer pipeline from session state. Call with NO arguments.

    Reads merged_evidence (or falls back to Monarch_output) and the original
    question from session state, then runs the extract → summarize → generate pipeline.
    """
    # Retrieve original question from query_plan stored by route_question
    query_plan = tool_context.state.get("query_plan", {})
    question = query_plan.get("question", "the biomedical question") if isinstance(query_plan, dict) else "the biomedical question"

    # Prefer merged_evidence; fall back to raw Monarch_output
    merged_evidence = tool_context.state.get("merged_evidence")
    if merged_evidence and isinstance(merged_evidence, dict) and (
        merged_evidence.get("nodes") or merged_evidence.get("edges")
    ):
        triples_result = format_merged_evidence(merged_evidence)
    else:
        monarch_output = tool_context.state.get("Monarch_output")
        if not monarch_output or not isinstance(monarch_output, dict):
            return {"error": "No merged_evidence or Monarch_output found in session state"}
        triples_result = extract_trapi_triples(monarch_output)

    summary = summarize_graph(triples_result)
    answer = generate_answer(question=question, summary=summary)
    return {"answer": answer, "triples": triples_result, "summary": summary}


# ============================================================================
# INFERENCE RUNNER (No Agent initialization here)
# ============================================================================

def run(question: str, trapi_message: dict) -> dict:
    """
    Executes the 3-tool pipeline:
      1. extract triples
      2. summarize graph (LLM)
      3. generate final answer (LLM)
    """
    print("[TRAPI-NLP] [PIPELINE] Running TRAPI NLP pipeline...")
    print(f"[TRAPI-NLP]    Question: {question}")
    
    triples_result = extract_trapi_triples(trapi_message)
    summary = summarize_graph(triples_result)
    answer = generate_answer(question=question, summary=summary)

    print("[TRAPI-NLP] [SUCCESS] Pipeline complete\n")
    
    return {
        "answer": answer,
        "triples": triples_result,
        "summary": summary
    }


# ============================================================================
# ADK ROOT AGENT (Only for web server)
# ============================================================================

explain_agent = Agent(
    name="trapi_nlp_answer_agent",
    model=LiteLlm(model="gpt-4o-mini"),
    instruction=(
        "You are a biomedical NLP assistant.\n\n"
        "Your ONLY job: call the `run_answer_pipeline` tool with NO arguments. "
        "It reads all evidence from session state and generates a natural language answer.\n\n"
        "Do NOT pass any arguments to `run_answer_pipeline`.\n"
        "After the tool call, return the 'answer' field from the result as your final response."
    ),
    tools=[run_answer_pipeline],
)
