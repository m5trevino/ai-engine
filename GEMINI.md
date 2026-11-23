# 🦚 PEACOCK ENGINE - System Context

## Project Overview
Peacock Engine is a high-performance, headless AI orchestration engine built with **Python (FastAPI)** and **Pydantic AI**. It acts as a unified gateway for multiple AI providers (Google Gemini, Groq, DeepSeek, Mistral), providing a standardized API for agentic strikes, chat, and filesystem interactions.

### Core Architecture
- **Backend (Python/FastAPI):**
  - `app/main.py`: Entry point, routing, and middleware configuration.
  - `app/core/striker.py`: The "Striker" module, responsible for model execution, usage tracking, cost calculation, and the "Hellcat Protocol" for performance throttling.
  - `app/core/key_manager.py`: Manages API key pools, rotation strategies (Shuffle, Round Robin), and 429-aware cooldowns.
  - `app/db/database.py`: SQLite persistence for key usage, conversation history, and app registrations.
  - `app/config.py`: Centralized model registry and performance mode definitions.
- **Frontend (React/Vite/Tailwind):**
  - Located in `ui/`, built into `app/static/`.
  - Provides a "Mission Control" dashboard for chatting, analytics, and system monitoring.
- **CLI (`ai-engine.py`):**
  - A comprehensive terminal interface for manual strikes, system audits, and onboarding new applications.

### Key Features
- **Multi-Gateway Support:** Unified interface for Groq, Google, DeepSeek, and Mistral.
- **Hellcat Protocol:** Proactive rate-limiting and performance modes (Stealth, Balanced, Apex).
- **Key Pooling:** Automatic rotation and health management of multiple API keys per provider.
- **Filesystem Bridge:** Secure access to local "Ammo" (context files) and "Prompts".
- **Structured Output:** Support for JSON and Pydantic-validated responses.

## Building and Running

### Prerequisites
- Python 3.10+
- Node.js & npm (for WebUI)
- `.env` file in the root with `GROQ_KEYS`, `GOOGLE_KEYS`, etc.

### Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the engine
python3 -m app.main
# or use the launcher
./launch.sh
```

### Frontend Setup
```bash
cd ui
npm install
npm run build  # Builds into app/static/ for FastAPI to serve
# For development with HMR:
npm run dev
```

### CLI Usage
```bash
# List models
python3 ai-engine.py models

# Execute a strike
python3 ai-engine.py strike "Explain quantum entanglement" --model gemini-3.1-flash

# Audit model health
python3 ai-engine.py audit
```

## Development Conventions

### Python Backend
- **Type Safety:** Use Pydantic models for all request/response schemas.
- **Logging:** Use `app.utils.formatter.CLIFormatter` for standardized, high-signal console output.
- **Database:** All persistent state should be managed via `app.db.database.get_db` context manager.
- **Gateways:** When adding a new provider, update `app/core/key_manager.py` and `app/config.py`.

### React Frontend
- **Styling:** Use Tailwind CSS utility classes.
- **Icons:** Use `lucide-react`.
- **Animations:** Use `framer-motion`.
- **API Communication:** Use `PeacockAPI` and `PeacockWS` in `ui/src/lib/api.ts`.

### Security
- **API Keys:** Never hardcode keys. They must be loaded from environment variables via `KeyPool`.
- **Paths:** Always expand user paths and validate existence before reading files in the filesystem bridge.

## Key Files
- `app/main.py`: API Entry Point.
- `app/core/striker.py`: Model Execution Logic.
- `app/core/key_manager.py`: Key Rotation & Pooling.
- `app/config.py`: Model Registry.
- `ai-engine.py`: Primary CLI Tool.
- `ui/src/App.tsx`: Main Frontend Component.
- `peacock.db`: SQLite Database File.
