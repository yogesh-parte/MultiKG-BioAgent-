# Testing the TRAPI NLP Answer Agent Locally

## Overview
This directory contains test files to validate the TRAPI NLP Answer Agent runner locally.

## Test Files

### 1. `test_trapi_message.json`
A TRAPI-compliant message representing a disease-gene association query for Parkinson disease (MONDO:0007254). The response format aligns with Monarch KG API structure and includes:

- **Query Graph**: Disease → Gene association query
- **Knowledge Graph**: 5 genes associated with Parkinson's disease:
  - SNCA (HGNC:11138)
  - PARK7 (HGNC:9211)
  - PINK1 (HGNC:8607)
  - PRKN (HGNC:9588)
  - LRRK2 (HGNC:6361)
- **Results**: Bindings showing each gene-disease association
- **Edge Attributes**: 
  - Publications (PMIDs)
  - Knowledge level (knowledge_assertion)
  - Evidence codes (ECO:0000304)
  - Source (infores:monarchinitiative)

### 2. `test_question.txt`
Natural language question: "What genes are associated with Parkinson disease?"

## Running the Test

### Command Line (using runner.py CLI)
```powershell
python runner.py --question "What genes are associated with Parkinson disease?" --trapi_file test_trapi_message.json
```

### Python Script
```python
from runner import run_local_sync
import json

with open('test_trapi_message.json', 'r') as f:
    trapi_message = json.load(f)

question = "What genes are associated with Parkinson disease?"
answer = run_local_sync(question, trapi_message)
print(answer)
```

### Using FastAPI (if running as a service)
```powershell
# Start the service
python runner.py

# In another terminal, POST the request
$body = @{
    question = "What genes are associated with Parkinson disease?"
    trapi_message = (Get-Content test_trapi_message.json | ConvertFrom-Json)
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri http://localhost:8000/answer -Method Post -Body $body -ContentType 'application/json'
```

## Expected Output
The agent should generate a natural language answer that:
- Lists the 5 genes associated with Parkinson disease
- Mentions evidence from publications (PMIDs)
- Notes the knowledge source (Monarch Initiative)
- Does NOT hallucinate information beyond what's in the TRAPI message
- Groups findings appropriately (e.g., noting these are gene-disease associations)

## TRAPI Format Alignment with Monarch KG
The test TRAPI message follows Monarch KG conventions:
- Uses Monarch CURIEs (MONDO for diseases, HGNC for genes)
- Includes `infores:monarchinitiative` as the primary knowledge source
- Uses BioLink model predicates (`biolink:gene_associated_with_condition`)
- Includes evidence codes (ECO) and publication references
- Follows TRAPI 1.4+ specification structure

## Troubleshooting
- Ensure the Google ADK agent is registered properly (check `agent.yaml`)
- Verify the `api_key` environment variable is set for Google AI API
- Check that all dependencies are installed (`uv sync` or `pip install -e .`)
