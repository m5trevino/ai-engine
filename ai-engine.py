"""
PEACOCK ENGINE - Command Line Interface
The main entry point for manual strikes, model management, and onboarding.
"""

import os
import sys
import asyncio
import argparse
import json
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn
import questionary
import socket
import sqlite3

from app.config import MODEL_REGISTRY
from app.core.striker import execute_strike
from app.utils.formatter import CLIFormatter, Colors
from app.core.key_manager import GroqPool, GooglePool, DeepSeekPool, MistralPool

console = Console()

def show_models():
    """List all available models in the registry."""
    table = Table(title="🦚 AI-ENGINE - MODEL REGISTRY")
    table.add_column("ID", style="cyan")
    table.add_column("Gateway", style="magenta")
    table.add_column("Tier", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Price (In/Out 1M)", style="dim")
    table.add_column("Note", style="white")

    for m in MODEL_REGISTRY:
        status_style = "green" if m.status == "active" else "red"
        price_str = f"${m.input_price_1m} / ${m.output_price_1m}"
        table.add_row(m.id, m.gateway, m.tier, f"[{status_style}]{m.status}[/]", price_str, m.note)
    
    console.print(table)

def show_keys():
    """List all loaded API keys."""
    pools = [
        ("GROQ", GroqPool),
        ("GOOGLE", GooglePool),
        ("DEEPSEEK", DeepSeekPool),
        ("MISTRAL", MistralPool)
    ]
    
    for name, pool in pools:
        if not pool.deck: continue
        table = Table(title=f"🔑 {name} KEY POOL")
        table.add_column("#", style="dim")
        table.add_column("Account / Label", style="yellow")
        table.add_column("Key (Masked)", style="cyan")
        
        for i, asset in enumerate(pool.deck):
            masked = f"{asset.key[:8]}..."
            table.add_row(str(i+1).zfill(2), asset.account, masked)
        
        console.print(table)
        print()

async def run_manual_strike(args):
    """Execute a strike from the CLI."""
    prompt = ""
    
    # 1. Resolve Prompt
    if args.prompt:
        prompt = args.prompt
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            console.print(f"[red]Error: File {args.file} not found.[/red]")
            return
        prompt = path.read_text(errors='ignore')
    else:
        console.print("[yellow]No prompt provided. Entering interactive input mode (Ctrl+D to finish):[/yellow]")
        prompt = sys.stdin.read()

    if not prompt:
        console.print("[red]Aborted: Empty prompt.[/red]")
        return

    # 2. Configure Environment for flags
    if args.quiet:
        os.environ["PEACOCK_QUIET"] = "true"
    
    if args.mode:
        os.environ["PEACOCK_PERF_MODE"] = args.mode
    
    if args.tunnel:
        os.environ["PEACOCK_TUNNEL"] = "true"
        console.print("[bold cyan]🛰️  TUNNEL MODE ACTIVE (SOCKS5: 127.0.0.1:1081)[/bold cyan]")
    
    # 3. Execute
    try:
        model_cfg = next((m for m in MODEL_REGISTRY if m.id == args.model), None)
        if not model_cfg:
            console.print(f"[red]Unknown Model ID: {args.model}[/red]")
            return

        console.print(f"[bold blue]⚡ INITIATING MANUAL STRIKE...[/bold blue]")
        
        result = await execute_strike(
            gateway=model_cfg.gateway,
            model_id=args.model,
            prompt=prompt,
            temp=args.temp,
            is_manual=True
        )
        
        # 4. Display Content (if not cli-off)
        if not args.no_print:
            console.print(Panel(str(result['content']), title=f"RESPONSE [{result['tag']}]", border_style="green"))
            
    except Exception as e:
        console.print(f"[bold red]STRIKE FAILED: {e}[/bold red]")

def run_onboarding():
    """True interactive multi-step onboarding for a new app."""
    import uuid
    from datetime import datetime
    
    console.print(Panel.fit("🚀 PEACOCK ENGINE - INTERACTIVE APP ONBOARDING", style="bold magenta"))
    
    # 1. Identity Collection
    app_name = questionary.text("What is the name of your new Application?").ask()
    if not app_name: return
    
    app_desc = questionary.text("Brief description of its mission:").ask()
    
    # 2. Tech Preferences
    model_choice = questionary.select(
        "Select your primary model for this integration:",
        choices=[m.id for m in MODEL_REGISTRY if m.status == "active"]
    ).ask()
    
    format_choice = questionary.select(
        "What is your preferred output format?",
        choices=["text", "json", "pydantic"]
    ).ask()

    # 3. Credentials & Registration
    app_id = f"APP-{uuid.uuid4().hex[:8].upper()}"
    api_secret = f"pk_v3_{uuid.uuid4().hex[:24]}"
    
    console.print(f"\n[cyan]Generating Integration Manifest for [bold]{app_name}[/bold]...[/cyan]")
    
    # 4. Generate Custom Manual
    manual_filename = f"{app_id}_INTEGRATION_MANUAL.md"
    manual_path = Path(manual_filename)
    
    # Get model info
    m = next((cfg for cfg in MODEL_REGISTRY if cfg.id == model_choice), None)
    
    manual_content = f"""# 🦚 PEACOCK INTEGRATION MANUAL: {app_name.upper()}
> **App ID**: `{app_id}`
> **Status**: INITIALIZED ({datetime.now().strftime('%Y-%m-%d %H:%M')})

## 📝 APP DESCRIPTION
{app_desc}

## 🔑 AUTHENTICATION
For local development, the engine is hosted at: `http://localhost:3099`
Use the following credentials in your requests:
- **App ID**: `{app_id}`
- **API Secret**: `{api_secret}` (Keep this secure)

## 🏎️ PREFERRED MODEL CONFIG
- **Model**: `{model_choice}`
- **Gateway**: `{m.gateway}`
- **Tier**: `{m.tier}`

## 🔌 INTEGRATION SNIPPET (PYTHON)
```python
import requests

def strike_engine(prompt):
    url = "http://localhost:3099/v1/chat"
    payload = {{
        "model": "{model_choice}",
        "prompt": prompt,
        "format": "{format_choice}",
        "temp": 0.7
    }}
    response = requests.post(url, json=payload)
    return response.json()

# Test the strike
result = strike_engine("System status check")
print(result['content'])
```

## 🛠️ UI SELECTOR CODE
Copy the dynamic flyout code generated by:
`./ai-engine flyout-snippet`

---
*Generated by PEACOCK ADM (App Discovery Module) V3*
"""
    manual_path.write_text(manual_content)
    
    # 5. Output Summary to CLI
    console.print(f"\n[bold green]✓ ONBOARDING COMPLETE![/bold green]")
    console.print(Panel(f"""
[bold]Integration Manual Created:[/bold] [yellow]{manual_filename}[/yellow]
Give this file to any agent or developer to start work.

[bold]App ID:[/bold] {app_id}
[bold]Secret:[/bold] {api_secret}
""", title="🏁 MISSION READY", border_style="green"))

def show_ui_guide():
    """Print chatbot-ready instructions for building a new UI."""
    guide = """
# PEACOCK ENGINE V3 - WEB UI BLUEPRINT
Role: Senior Frontend Engineer
Task: Build a new Web UI for the Peacock Engine.

## Backend Specs:
- Base URL: http://localhost:3099
- Format: JSON REST API

## Core Endpoints:
1. GET /v1/chat/models - Returns all models grouped by gateway.
2. POST /v1/chat - Unified strike endpoint.
   Payload: { "model": "id", "prompt": "text", "temp": 0.7 }
3. GET /health - Engine and Key status.

## UI Requirements:
- Flyout/Dropdown model selector organized by Gateway.
- Real-time token counter (In/Out/Total).
- Markdown rendering for AI responses.
- Cost-per-strike display.
- Independent Toggles for: Success Logs, Failed Logs, Stealth Mode.
"""
    console.print(Panel(guide, title="🤖 CHATBOT-READY UI GUIDE", border_style="cyan"))

def show_flyout_snippet():
    """Dynamically generate a premium, gateway-organized model selector UI."""
    # Group models by gateway
    by_gateway = {}
    for m in MODEL_REGISTRY:
        if m.status != "active": continue
        gw = m.gateway.upper()
        if gw not in by_gateway:
            by_gateway[gw] = []
        by_gateway[gw].append(m)

    # Build HTML sections
    sections = ""
    for gw, models in by_gateway.items():
        color = "blue" if gw == "GOOGLE" else "orange" if gw == "GROQ" else "purple" if gw == "DEEPSEEK" else "green"
        sections += f"""
    <!-- {gw} SECTION -->
    <div class="p-2 border-b border-gray-800 last:border-0">
      <div class="text-[10px] uppercase tracking-widest text-{color}-400 font-bold mb-1 ml-2">{gw}</div>
      <div class="space-y-1">"""
        for m in models:
            sections += f"""
        <button class="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-{color}-900/30 hover:text-{color}-200 rounded-md transition-colors" onclick="setModel('{m.id}')">{m.id}</button>"""
        sections += """
      </div>
    </div>"""

    snippet = f"""
<!-- PEACOCK DYNAMIC MODEL SELECTOR (Tailwind/HTML) -->
<div class="relative group">
  <button class="bg-gray-800 text-white px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-gray-700 transition-all border border-gray-600">
    <span id="current-model">Select Model</span>
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"></path></svg>
  </button>
  
  <div class="absolute hidden group-hover:block left-0 mt-2 w-72 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden backdrop-blur-md">
    {sections}
  </div>
</div>

<script>
function setModel(id) {{
  console.log("PEACOCK: Model Selected -> " + id);
  document.getElementById('current-model').innerText = id;
  // Your implementation: window.peacockModel = id;
}}
</script>
"""
    console.print(Panel(Syntax(snippet, "html", theme="monokai"), title="🚀 DYNAMIC MULTI-GATEWAY FLYOUT"))

def show_mission_control():
    """The Ultimate Source of Truth: Diagnostics, Documents, and Context for AI Agents."""
    from app.routes.docs import ENDPOINTS
    import socket
    import sqlite3
    
    # 1. AGENT INSTRUCTION HEADER
    header = """
> [!IMPORTANT]
> **AGENT DIRECTIVE**: You have entered PEACOCK MISSION CONTROL.
> Use the data below to identify system state, available hardware (models), and integration patterns.
> To fix or update an app, cross-reference the **Technical Manual** with the **Live Diagnostics**.
"""

    # 2. DOCUMENT AGGREGATION
    root = Path(__file__).resolve().parent
    docs = {}
    doc_paths = {
        "MISSION_MANIFEST.md": root / "MISSION_MANIFEST.md",
        "app/TACTICAL_COMMAND.md": root / "app" / "TACTICAL_COMMAND.md",
        "app/AGENT_ONBOARDING.md": root / "app" / "AGENT_ONBOARDING.md"
    }
    for label, path in doc_paths.items():
        docs[label] = path.read_text() if path.exists() else f"File {label} not found at {path}."

    # 3. LIVE DIAGNOSTICS
    # Port Check
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    port_status = "[bold green]ONLINE[/bold green]" if s.connect_ex(('127.0.0.1', 3099)) == 0 else "[bold red]OFFLINE (Start with ./run_engine.sh)[/bold red]"
    s.close()

    # DB Check
    db_status = "[bold green]HEALTHY[/bold green]"
    try:
        conn = sqlite3.connect("peacock.db")
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        db_status = "[bold red]DATABASE ERROR[/bold red]"

    # Key Pools
    pool_info = f"GROQ: {len(GroqPool.deck)} | GOOGLE: {len(GooglePool.deck)} | DEEPSEEK: {len(DeepSeekPool.deck)} | MISTRAL: {len(MistralPool.deck)}"

    diagnostics = f"""
## 🩺 LIVE DIAGNOSTICS
- **Engine Port (3099)**: {port_status}
- **Database (peacock.db)**: {db_status}
- **Key Pool Integrity**: {pool_info}
- **Tunnel Mode**: {"[cyan]ENABLED[/cyan]" if os.getenv("PEACOCK_TUNNEL") == "true" else "DISABLED"}
- **Current Node**: {os.uname().nodename}
"""

    # 4. TELEMETRY (Last 3 Strikes)
    success_path = Path("success_strikes.log")
    recent_success = "None"
    if success_path.exists():
        lines = success_path.read_text().splitlines()
        recent_success = "\n".join(lines[-3:]) if lines else "Empty"

    telemetry = f"""
## 📡 RECENT TELEMETRY (Last 3 Successes)
```text
{recent_success}
```
"""

    # 5. OUTPUT
    full_dump = f"""
{header}

# 🌌 MISSION CONTROL - PEACOCK ENGINE V3

{diagnostics}

{telemetry}

## 📜 MISSION MANIFEST
{docs["MISSION_MANIFEST.md"]}

## 🛠️ TACTICAL COMMAND MANUAL
{docs["app/TACTICAL_COMMAND.md"]}

## 🤖 AGENT ONBOARDING GUIDE
{docs["app/AGENT_ONBOARDING.md"]}
"""
    console.print(Panel(full_dump, title="🎮 MISSION CONTROL: TOTAL EMPOWERMENT", border_style="bold magenta"))

def run_agent_guide():
    """Interactive guided walkthrough for agents or humans."""
    console.print(Panel.fit("🤖 PEACOCK AGENT INTERROGATOR", style="bold cyan"))
    
    mission = questionary.select(
        "What is your primary mission?",
        choices=[
            {"name": "Setup a New Application", "value": "setup"},
            {"name": "Repair/Update an Existing Integration", "value": "repair"},
            {"name": "Quick API Reference (Endpoints & Payloads)", "value": "api"},
            {"name": "UI Snippets (Flyouts & Dropdowns)", "value": "ui"}
        ]
    ).ask()
    
    if mission == "setup":
        console.print("[cyan]Initializing SETUP Flow...[/cyan]")
        run_onboarding()
    elif mission == "repair":
        console.print("[yellow]Initializing REPAIR Flow...[/cyan]")
        print("1. Run `./ai-engine audit` to check model health.")
        print("2. Check `vault/failed/` for the last error log.")
        print("3. Run `./ai-engine mc` for full diagnostic context.")
    elif mission == "api":
        show_dossier()
    elif mission == "ui":
        show_flyout_snippet()
        show_ui_guide()

def show_dossier():
    """Print a comprehensive, AI-readable dossier of the entire engine."""
    from app.routes.docs import ENDPOINTS
    
    # 1. Header & Mission
    mission_path = Path("MISSION_MANIFEST.md")
    mission_text = mission_path.read_text() if mission_path.exists() else "Mission Manifest not found."
    
    # 2. Model Registry Summary
    models_summary = "| ID | Gateway | Tier | rpm | tpm |\n|---|---|---|---|---|\n"
    for m in MODEL_REGISTRY:
        models_summary += f"| {m.id} | {m.gateway} | {m.tier} | {m.rpm} | {m.tpm} |\n"
    
    # 3. API Endpoints Summary
    endpoints_summary = "| Path | Method | Purpose |\n|---|---|---|\n"
    for ep in ENDPOINTS:
        endpoints_summary += f"| {ep['path']} | {ep['method']} | {ep['description']} |\n"
        
    dossier = f"""
# 🦚 PEACOCK ENGINE V3: SYSTEM DOSSIER
This document is optimized for AI Agent consumption. It contains the precise technical specs and integration patterns for the entire orchestration layer.

{mission_text}

## 🏎️ MODEL REGISTRY (MARCH 2026 FLEET)
{models_summary}

## 🔌 API ENDPOINTS
{endpoints_summary}

## 🛠️ CORE INTEGRATION PATTERN
Use `POST /v1/chat` for all new apps.
```json
{{
  "model": "gemini-3.1-flash-lite",
  "prompt": "Your instruction",
  "format": "text",
  "temp": 0.7
}}
```

## 📂 FORENSIC LOGGING
- Success: `vault/successful/PEA-XXXX.txt`
- Failure: `vault/failed/PEA-XXXX.txt`
"""
    console.print(Panel(dossier, title="📂 AGENT-READY MISSION DOSSIER", border_style="bold green"))

async def run_audit(args):
    """Test the health of one or more models and offer to freeze failures."""
    targets = []
    if args.id:
        targets = [m for m in MODEL_REGISTRY if m.id == args.id]
    elif args.gateway:
        targets = [m for m in MODEL_REGISTRY if m.gateway == args.gateway]
    else:
        # Defaults to active models
        targets = [m for m in MODEL_REGISTRY if m.status == "active"]

    if not targets:
        console.print("[red]No matching active models found to audit.[/red]")
        return

    console.print(Panel.fit(f"🔍 AUDITING {len(targets)} MODELS", style="bold cyan"))
    
    failed_models = []
    
    for m in targets:
        # Skip embedding/whisper models for basic text audit for now
        if "embedding" in m.id or "whisper" in m.id:
            console.print(f"[dim]Skipping specialized model: {m.id}[/dim]")
            continue

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task(description=f"Striking {m.id}...", total=None)
            try:
                # Use a very short, cheap prompt for audit
                result = await execute_strike(
                    gateway=m.gateway,
                    model_id=m.id,
                    prompt="respond with 'OK'",
                    temp=0.0,
                    is_manual=True
                )
                progress.update(task, description=f"[green]✅ {m.id} is ONLINE[/green] ({result['tag']})")
            except Exception as e:
                error_msg = str(e)
                progress.update(task, description=f"[red]❌ {m.id} is DOWN[/red]")
                console.print(f"   [dim]Error: {error_msg[:120]}[/dim]")
                failed_models.append({"id": m.id, "error": error_msg})

    # Interactive Decommissioning
    if failed_models:
        console.print(f"\n[bold yellow]⚠ ATTENTION:[/bold yellow] {len(failed_models)} models are currently failing health checks.")
        
        do_freeze = questionary.confirm("Would you like to decommission (freeze) any of these models?").ask()
        if do_freeze:
            choices = [f"{f['id']} (Error: {f['error'][:50]})" for f in failed_models]
            selected_raw = questionary.checkbox(
                "Select models to FREEZE (decommission):",
                choices=choices
            ).ask()
            
            if selected_raw:
                # Extract IDs back from choices string
                to_freeze = [s.split(" (")[0] for s in selected_raw]
                run_freeze_bulk(to_freeze)

def run_freeze_bulk(model_ids: List[str]):
    """Freeze multiple models at once."""
    from app.config import FROZEN_FILE, FROZEN_IDS
    
    newly_frozen = []
    for mid in model_ids:
        if mid not in FROZEN_IDS:
            FROZEN_IDS.append(mid)
            newly_frozen.append(mid)
    
    if newly_frozen:
        FROZEN_FILE.write_text(json.dumps(FROZEN_IDS, indent=4))
        console.print(f"[bold green]✓ DECOMMISSIONED {len(newly_frozen)} MODELS:[/bold green]")
        for mid in newly_frozen:
            console.print(f"  - [red]{mid}[/red]")
        console.print("[dim]Restart the engine to fully apply these status changes to the API server.[/dim]")
    else:
        console.print("[yellow]No new models were frozen.[/yellow]")

def run_unfreeze(model_id: str):
    """Re-activate a frozen model."""
    from app.config import FROZEN_FILE, FROZEN_IDS
    if model_id in FROZEN_IDS:
        FROZEN_IDS.remove(model_id)
        FROZEN_FILE.write_text(json.dumps(FROZEN_IDS, indent=4))
        console.print(f"[bold green]✓ MODEL RE-ACTIVATED:[/bold green] [cyan]{model_id}[/cyan]")
    else:
        console.print(f"[yellow]Model '{model_id}' is not currently frozen.[/yellow]")

def run_ui():
    """Boot the engine and open the Web UI."""
    import subprocess
    import webbrowser
    import time
    from pathlib import Path
    
    console.print()
    console.print("[bold cyan]✦ Waking up the Synthetic Architect...[/bold cyan]")
    
    script_path = Path(__file__).resolve().parent / "run_engine.sh"
    
    try:
        p = subprocess.Popen(["bash", str(script_path)], cwd=str(script_path.parent))
        console.print("[dim]Waiting for engine ignition sequence...[/dim]")
        time.sleep(3)
        console.print("[bold green]✓ Firing up the Web UI...[/bold green]")
        webbrowser.open("http://localhost:3099/chat")
        p.wait()
    except KeyboardInterrupt:
        console.print("\n[bold red]Shutting down Synthetic Architect...[/bold red]")

def main():
    parser = argparse.ArgumentParser(description="AI-ENGINE CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Models
    subparsers.add_parser("models", help="List available models")
    
    # Keys
    subparsers.add_parser("keys", help="List loaded API keys")

    # Audit
    audit_p = subparsers.add_parser("audit", help="Check model health")
    audit_p.add_argument("--gateway", "-g", help="Audit specific gateway")
    audit_p.add_argument("--id", help="Audit specific model ID")

    # Strike
    strike_p = subparsers.add_parser("strike", help="Execute an AI strike")
    strike_p.add_argument("prompt", nargs="?", help="Direct prompt text")
    strike_p.add_argument("--file", "-f", help="Path to payload file")
    strike_p.add_argument("--model", "-m", default="gemini-3.1-flash-lite", help="Model ID")
    strike_p.add_argument("--temp", "-t", type=float, default=0.7, help="Temperature")
    strike_p.add_argument("--no-print", action="store_true", help="Don't print output to CLI")
    strike_p.add_argument("--quiet", "-q", action="store_true", help="Silence debug info")
    strike_p.add_argument("--tunnel", action="store_true", help="Use MetroPCS TUN0 SOCKS5 Proxy")
    strike_p.add_argument("--mode", choices=["stealth", "balanced", "apex"], default="balanced", help="Performance Mode (Hellcat Protocol)")

    # Onboarding
    subparsers.add_parser("onboard", help="Guide to setup a new application")
    
    # UI Guides
    subparsers.add_parser("ui-guide", help="Instructions for chatbots to build a UI")
    subparsers.add_parser("flyout-snippet", help="Get the pro model-selector HTML snippet")
    subparsers.add_parser("dossier", help="Print a comprehensive, AI-readable system briefing")
    
    # Mission Control
    mc_p = subparsers.add_parser("mission-control", aliases=["mc"], help="Total system context dump for agents")
    
    # Agent Guide
    subparsers.add_parser("agent-guide", help="Interactive mission briefing for agents")

    # Freeze/Unfreeze
    freeze_p = subparsers.add_parser("freeze", help="Decommission a model")
    freeze_p.add_argument("id", help="Model ID to freeze")
    
    unfreeze_p = subparsers.add_parser("unfreeze", help="Re-activate a decommissioned model")
    unfreeze_p.add_argument("id", help="Model ID to unfreeze")

    # UI Launcher
    subparsers.add_parser("ui", help="Boot the engine and open the Web UI")

    # Test Commands
    from app.commands.test_commands import add_test_subparser, add_tokens_subparser
    add_test_subparser(subparsers)
    add_tokens_subparser(subparsers)

    args = parser.parse_args()

    if args.command == "models":
        show_models()
    elif args.command == "keys":
        show_keys()
    elif args.command == "strike":
        asyncio.run(run_manual_strike(args))
    elif args.command == "audit":
        asyncio.run(run_audit(args))
    elif args.command == "onboard":
        run_onboarding()
    elif args.command == "ui-guide":
        show_ui_guide()
    elif args.command == "flyout-snippet":
        show_flyout_snippet()
    elif args.command == "dossier":
        show_dossier()
    elif args.command == "mission-control" or args.command == "mc":
        show_mission_control()
    elif args.command == "agent-guide":
        run_agent_guide()
    elif args.command == "freeze":
        run_freeze_bulk([args.id])
    elif args.command == "unfreeze":
        run_unfreeze(args.id)
    elif args.command == "ui":
        run_ui()
    elif args.command == "test":
        if hasattr(args, 'func'):
            args.func(args)
        else:
            console.print("[yellow]Use: ai-engine test google | groq | all[/yellow]")
    elif args.command == "tokens":
        if hasattr(args, 'func'):
            args.func(args)
        else:
            console.print("[yellow]Use: ai-engine tokens count --text \"hello\"[/yellow]")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
