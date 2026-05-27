# Reversal Intelligence Engine

**A production-grade, graph-driven AI workflow framework for automated financial analysis and investment decision support.**

---

## Overview

The Reversal Intelligence Engine (RIE) is an enterprise AI orchestration framework designed to automate multi-stage financial research workflows. It ingests raw stock screener data, enriches it with live market fundamentals, processes it through a structured signal pipeline, and routes each candidate through an adversarial multi-agent reasoning system — producing investment-grade recommendations with a full audit trail.

The framework is built around a clean architectural separation: a **domain-agnostic execution engine** and a **domain-specific strategy layer**. This means the core workflow runtime can be reused across any structured decision-making domain — financial analysis, credit underwriting, insurance risk, and beyond.

---

## Architecture

```
                        ┌─────────────────────────────┐
                        │        REST API Layer        │
                        │          (FastAPI)           │
                        └──────────────┬──────────────┘
                                       │
                        ┌──────────────▼──────────────┐
                        │      Workflow Orchestrator   │
                        │  Scheduler (DAG) + Executor  │
                        │     (Parallel ThreadPool)    │
                        └──────────────┬──────────────┘
                                       │
        ┌──────────────────────────────▼──────────────────────────────┐
        │                        Node Pipeline                        │
        │                                                             │
        │  INGEST ──► ENRICHMENT ──► SIGNAL ──► DEBATE ──► WATCHLIST  │
        │                                                             │
        │  CSV/API     yfinance      4-Channel   Bull Agent   JSON +  │
        │  Screener    Fundamentals  Processing  Bear Agent   Audit   │
        │  Candidates  PE, ROE, EPS  Valuation   Judge Agent  Trail   │
        │              Earnings      Technical                        │
        │              Debt Ratios   Profitability                    │
        │                            News Sentiment                   │
        └─────────────────────────────────────────────────────────────┘
```

The pipeline is defined as a **directed acyclic graph (DAG)**. Each node declares its dependencies; the scheduler resolves execution order and the executor runs independent nodes in parallel.

---

## Adversarial AI Reasoning Model

The core differentiator of this system is its **three-agent debate architecture**. Rather than relying on a single LLM call, every stock candidate is evaluated through an adversarial reasoning loop:

```
                         ┌─────────────────┐
                         │   Stock Data +  │
                         │   Signal Layer  │
                         └────────┬────────┘
                                  │
               ┌──────────────────┴──────────────────┐
               ▼                                     ▼
    ┌─────────────────────┐             ┌─────────────────────┐
    │      Bull Agent     │             │      Bear Agent     │
    │                     │             │                     │
    │  Constructs upside  │             │  Stress-tests risk  │
    │  thesis, identifies │             │  factors, downside  │
    │  catalysts and      │             │  scenarios and      │
    │  entry rationale    │             │  structural flaws   │
    └──────────┬──────────┘             └──────────┬──────────┘
               │                                   │
               └──────────────┬────────────────────┘
                              ▼
                   ┌─────────────────────┐
                   │     Judge Agent     │
                   │                     │
                   │  Synthesizes both   │
                   │  arguments into a   │
                   │  structured verdict │
                   │                     │
                   │  STRONG_BUY         │
                   │  BUY           ─────┼──► Watchlist Output
                   │  HOLD               │
                   │  SELL               │
                   │  STRONG_SELL        │
                   └─────────────────────┘
```

This pattern mirrors adversarial evaluation frameworks used in AI safety research and institutional investment committee structures.

---

## Project Structure

```
reversal_intelligence_engine/
│
├── engine/                          # Domain-agnostic execution framework
│   ├── scheduler.py                 # DAG traversal and node ordering
│   ├── executor.py                  # Parallel node execution (ThreadPoolExecutor)
│   ├── nodes/node_base.py           # Abstract base class for all nodes
│   ├── state/                       # Shared workflow state
│   ├── context/                     # Runtime context (config, credentials, run_id)
│   └── llm/parser.py                # LLM response parsing utilities
│
├── reversal_strategy/               # Financial domain layer
│   ├── graph/graph_config.py        # Workflow DAG definition
│   ├── registry/node_registry.py    # Node name → class resolution
│   ├── agents/
│   │   ├── llm_client.py            # OpenAI gateway with token and cost tracking
│   │   ├── bull_agent.py            # Bullish thesis generation
│   │   ├── bear_agent.py            # Risk and downside analysis
│   │   └── judge_agent.py           # Final verdict synthesis
│   └── nodes/
│       ├── ingest_node.py           # Stock candidate ingestion
│       ├── enrichment_node.py       # Live fundamental data enrichment
│       ├── financial_signal_node.py # Multi-channel signal processing
│       ├── debate_node.py           # Adversarial agent orchestration
│       └── watchlist_node.py        # Output persistence and audit logging
│
├── domain/                          # Typed contracts and business objects
│   ├── entities/                    # Core domain entities
│   ├── models/                      # Pydantic data models
│   ├── dto/                         # API data transfer objects
│   ├── contracts/                   # Output schemas and parsers
│   └── ingestion/                   # Input format adapters
│
└── infrastructure/                  # External system integrations
    ├── api/main.py                  # FastAPI application entry point
    ├── config/                      # Environment and runtime configuration
    ├── adapters/                    # Storage and service adapters
    └── observability/               # Logging and tracing
```

---

## Workflow Configuration

The pipeline topology is declared in a single configuration file. No workflow logic is embedded in the engine — it reads the graph at runtime.

```python
# reversal_strategy/graph/graph_config.py

GRAPH = {
    "nodes": ["INGEST", "ENRICHMENT", "SIGNAL", "DEBATE", "WATCHLIST"],
    "edges": {
        "INGEST":      [],
        "ENRICHMENT":  ["INGEST"],
        "SIGNAL":      ["ENRICHMENT"],
        "DEBATE":      ["SIGNAL"],
        "WATCHLIST":   ["DEBATE"],
    }
}
```

Adding a new processing step requires two changes: a new `NodeBase` subclass and one additional entry in the graph config. The execution engine requires no modification.

---

## Sample Output

Each processed stock produces a structured record with full reasoning transparency and cost accounting:

```json
{
  "ticker": "AAPL",
  "recommendation": "BUY",
  "confidence_score": 0.82,
  "bull_thesis": "Strong earnings momentum with improving margin profile. Undervalued relative to sector peers on a PEG basis. Technical structure suggests accumulation above the 200-day moving average.",
  "bear_thesis": "Elevated valuation multiple at current rate environment. Margin compression risk from supply chain restructuring. Regulatory overhang in EU markets.",
  "judge_verdict": "Bull case is structurally stronger. Entry is supported at current levels with moderate position sizing. Bear risks are acknowledged but not thesis-breaking at this stage.",
  "signals": {
    "valuation":       "ATTRACTIVE",
    "profitability":   "STRONG",
    "technical":       "BULLISH",
    "news_sentiment":  "POSITIVE"
  },
  "audit": {
    "run_id":             "2026-05-22T10:30:00Z",
    "tokens_used":        3420,
    "cost_usd":           0.0068,
    "processing_time_ms": 4200
  }
}
```

---

## Running the System

**Requirements**
```bash
pip install -r requirements.txt
```

**Set environment variables**
```powershell
$env:OPENAI_API_KEY = "sk-..."
```

**Run the full workflow from the command line**
```bash
python -m reversal_intelligence_engine.main
```

**Start the API server**
```powershell
.\run_api.ps1
# or
uvicorn reversal_intelligence_engine.infrastructure.api.main:app --reload --port 8000
```

**API Endpoints**

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/run-workflow` | Trigger a full pipeline run |
| `GET` | `/watchlist` | Retrieve latest recommendations |
| `GET` | `/docs` | Interactive API documentation (Swagger UI) |

---

## Design Principles

**Separation of Concerns**
The execution engine has no knowledge of financial logic. The strategy layer has no knowledge of threading or scheduling. Each layer is independently testable and replaceable.

**Open for Extension, Closed for Modification**
New analysis nodes can be added without touching the engine. The `NodeBase` contract defines a stable interface; all complexity lives inside individual node implementations.

**Config-Driven Topology**
Workflow structure is a runtime configuration, not compiled logic. Teams can modify, extend, or branch pipelines without requiring engineering changes to the core framework.

**Full Observability**
Every workflow run produces a structured audit log: which nodes executed, in what order, at what cost, and what each AI agent concluded. This satisfies compliance and governance requirements in regulated environments.

**Graceful Isolation**
Node failures do not cascade. The executor isolates failures per node and reports them without halting the rest of the pipeline.

---

## Applicability Beyond Finance

The engine layer is entirely domain-agnostic. The financial strategy is one instance of a general pattern. The same framework supports:

| Domain | Workflow Analogy |
|---|---|
| Credit Underwriting | Replace financial signals with credit bureau and behavioral signals |
| Insurance Risk Assessment | Replace debate agents with actuarial and claims-history agents |
| Regulatory Compliance Screening | Replace watchlist with compliance flag and evidence trail |
| Supply Chain Risk | Replace enrichment with vendor financial and geopolitical signals |
| Clinical Decision Support | Replace stock candidates with patient cohorts and signals with diagnostic markers |

---

## Roadmap

| Priority | Item | Description |
|---|---|---|
| High | Real-time streaming | WebSocket-based node progress events |
| High | Persistent storage | Replace JSON output with relational or document DB |
| Medium | Multi-model routing | Per-agent model selection (GPT-4o, Claude, Gemini) |
| Medium | Dynamic graph rewriting | Conditional node insertion based on intermediate results |
| Medium | Vector memory layer | Longitudinal agent reasoning across pipeline runs |
| Low | Infrastructure hardening | Kubernetes deployment, autoscaling, observability stack |

---

## Development History

This system was developed over a 31-day engineering sprint, progressing from foundational LLM integration patterns through increasingly complex agent architectures. The final design draws from:

- Graph-based workflow orchestration patterns (Apache Airflow, LangGraph)
- Durable execution concepts (Temporal.io)
- Adversarial evaluation frameworks from AI safety research
- Enterprise domain-driven design principles

---

> *Structured AI workflows outperform single-model prompts in reliability, auditability, and production suitability. This framework is built on that premise.*
