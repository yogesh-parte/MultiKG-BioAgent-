# Suggested folder structure

```ascii
multi-kg-biomed-chatbot/
  ├── README.md
  ├── LICENSE
  ├── CONTRIBUTING.md
  ├── pyproject.toml
  ├── .gitignore
  ├── .github/
  │   └── workflows/
  │       └── ci.yml
  ├── assets/
  │   ├── banner.png              # copy your poster here
  │   └── logo.png                # optional small crop
  ├── docs/
  │   ├── PROJECT_PROPOSAL.md
  │   ├── ARCHITECTURE.md
  │   ├── AGENTS.md
  │   ├── KGS_INTEGRATION.md
  │   ├── TRAPI_EXAMPLES.md
  │   └── ROADMAP.md
  ├── agents/
  │   ├── __init__.py
  │   ├── chatfront_agent
  │   ├── query_graph_builder_agent
  │   ├── orchestrator_agent
  │   ├── monarch_agent
  │   ├── clinical_connections_agent
  │   ├── biggim_agent
  │   ├── drug_approvals_agent
  │   ├── clinical_trials_agent
  │   ├── wellness_multiomics_agent
  │   ├── evidence_merger_agent
  │   └── explanation_agent
  ├── tools/
  │   ├── __init__.py
  │   ├── http_utils.py
  │   ├── monarch_tool.py
  │   ├── translator_kp_tool.py
  │   └── reasoner_trapi_tool.py
  ├── datasets/
  │   └──  __init__.py
  ├── workflows/
  │   └── disease_gene_drug_workflow.yaml
  ├── app/
  │   ├── __init__.py
  │   └── main.py
  └── tests/
      ├── __init__.py
      ├── test_trapi_examples.py
      └── test_monarch_tool.py
```

