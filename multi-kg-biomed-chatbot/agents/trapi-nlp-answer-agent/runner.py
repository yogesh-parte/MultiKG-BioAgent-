import json
import asyncio
from pathlib import Path
from typing import Any, Dict

from google import genai
from google.genai import types  # ADK datatypes
from fastapi import FastAPI
from pydantic import BaseModel

# --------------------------
# Load Agent Config
# --------------------------

AGENT_NAME = "trapi-nlp-answer-agent"
AGENT_DIR = Path(__file__).parent
AGENT_CONFIG_FILE = AGENT_DIR / "agent.yaml"

client = genai.Client()

# Register the agent from YAML definition
agent_registry = client.agents.register(
    name=AGENT_NAME,
    config=str(AGENT_CONFIG_FILE)
)

agent = agent_registry[AGENT_NAME]


# --------------------------
# Local Runner (Convenience API)
# --------------------------

async def run_local(question: str, trapi_message: Dict[str, Any]):
    """
    Local async runner. Pass question + TRAPI JSON, get the KG-derived
    natural-language answer.
    """
    request_payload = {
        "question": question,
        "trapi_message": trapi_message
    }

    result = await agent.run_async(request_payload)
    return result.output


def run_local_sync(question: str, trapi_message: Dict[str, Any]):
    """
    Sync wrapper for notebooks / scripts.
    """
    return asyncio.run(run_local(question, trapi_message))


# --------------------------
# Optional FastAPI Service
# --------------------------

class QueryRequest(BaseModel):
    question: str
    trapi_message: Dict[str, Any]


app = FastAPI(
    title="TRAPI NLP Answer Agent",
    description="Google ADK runner for generating NLP answers from TRAPI graphs.",
    version="1.0.0"
)


@app.post("/answer")
async def answer(req: QueryRequest):
    """
    POST endpoint:
    {
      "question": "...",
      "trapi_message": {...}
    }
    """
    result = await agent.run_async(req.dict())
    return {
        "answer": result.output,
        "agent": AGENT_NAME
    }


# --------------------------
# CLI Entrypoint
# --------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run TRAPI NLP Answer Agent locally.")
    parser.add_argument("--question", required=True, help="Biomedical question")
    parser.add_argument("--trapi", required=True, help="Path to TRAPI JSON file")
    args = parser.parse_args()

    with open(args.trapi, "r") as f:
        trapi_json = json.load(f)

    print("\n>>> Running TRAPI NLP Answer Agent...\n")
    answer_text = run_local_sync(args.question, trapi_json)
    print("=== Final Answer ===\n")
    print(answer_text)