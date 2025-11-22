

```mermaid

flowchart TD
  U[User] --> CF[Chatfront Agent]

  CF --> QG[Query Graph Builder Agent<br/>(ReasonerAPI / TRAPI message)]
  QG --> ORCH[Multi-KG Orchestrator Agent]

  ORCH --> M1[Monarch KG Agent]
  ORCH --> C1[Clinical Connections KG Agent]
  ORCH --> B1[BigGIM Drug Response KG Agent]
  ORCH --> D1[Drug Approvals KG Agent]
  ORCH --> T1[Clinical Trials KG Agent]
  ORCH --> W1[Wellness Multiomics KG Agent]

  M1 --> EV[Evidence Merger Agent]
  C1 --> EV
  B1 --> EV
  D1 --> EV
  T1 --> EV
  W1 --> EV

  EV --> EXP[Explanation & Summarisation Agent]
  EXP --> CF
  CF --> U
  ```