# 🧠 PEACOCK ENGINE V2
**Headless AI Orchestrator (Python Refactor)**

## MISSION
To serve as the central nervous system for all FlintX AI operations. This version is built with **Python (FastAPI)** and **Pydantic AI** for high-stakes agentic strikes and type-safe LLM integration.

## SETUP
1.  Ensure `~/.env.global` is loaded in your shell or `.env` exists in the root.
2.  Create virtual environment: `python3 -m venv venv`
3.  Activate: `source venv/bin/activate`
4.  Install dependencies: `pip install -r requirements.txt`
5.  Run server: `python3 -m app.main`

## ENDPOINTS
*   `POST /v1/strike`: Execute a prompt via Pydantic AI agents.
*   `GET /v1/models`: Get available models from the registry.
*   `GET/POST/DELETE /v1/fs`: Filesystem bridge for Ammo and Prompts.

