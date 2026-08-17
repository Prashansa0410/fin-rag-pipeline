# FinResearch AI

FinResearch AI is an intelligent Retrieval-Augmented Generation (RAG) pipeline designed for financial operations, compliance, and policy documentation. It provides a robust architecture that automatically balances LLM cost, latency, and reasoning complexity by routing queries to different model tiers based on their complexity.

## Key Features

- **Intelligent Query Routing:** Dynamically routes queries to Economical, Standard, or Advanced model tiers.
- **Autonomous Conflict Detection:** Automatically detects conflicting evidence across multiple retrieved documents (e.g., superseding policies like `v1` vs `v2`) and escalates to advanced reasoning tiers when contradictions are found.
- **Cost & Latency Tracking:** Full observability into token consumption, inference latency, and routing savings per request.
- **Hybrid Search:** Combines pgvector semantic search with keyword ranking for robust retrieval accuracy.
- **Deterministic Extraction:** Pre-analyzes queries for metadata (like business domain or specific partners) to filter vector searches efficiently without wasting LLM tokens.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL (pgvector + full-text search)
- **AI / LLM Integration:** Hugging Face `InferenceClient` (supporting dynamic open-source models like Llama 3.1 and Qwen 2.5)
- **Frontend:** Next.js, React, Tailwind CSS
- **Infrastructure:** Docker & Docker Compose

## Quickstart

1. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
2. Add your Hugging Face Access Token to the `.env` file:
   ```env
   HF_TOKEN=your_huggingface_token
   ```
3. Start the application using Docker Compose:
   ```bash
   docker compose up -d
   ```
4. Access the API at `http://localhost:8000` and the web interface at `http://localhost:3000`.

## Architecture Details

- **Model Registry (`backend.llm.registry`)**: Manages the available models and their capability scores, input/output costs, and latency classes.
- **Router (`backend.routing.router`)**: Analyzes the query intent (e.g., Simple Fact vs High Risk) and the retrieval confidence to pick the most cost-effective tier.
- **Confidence Analyzer (`backend.retrieval.confidence`)**: Inspects the retrieved context for explicit numeric conflicts (like differing settlement windows) across disjoint documents.

## Running Evaluations

To run the built-in evaluation suite and test the intelligent routing logic:
```bash
docker compose exec backend python -m backend.evaluation.run
```
