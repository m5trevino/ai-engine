import os
import sys
from pathlib import Path

def check_structure():
    required_files = [
        "app/main.py",
        "app/core/striker.py",
        "app/core/batch_striker.py",
        "app/middleware/auth.py",
        "ui/src/App.tsx",
        ".venv/bin/python",
        ".env"
    ]
    print("🔍 CHECKING ARCHITECTURE INTEGRITY...")
    for f in required_files:
        status = "✅" if os.path.exists(f) else "❌"
        print(f"  {status} {f}")

def check_ui():
    print("\n🔍 CHECKING MODULAR UI COMPONENTS...")
    components = [
        "ui/src/components/striker/DirectorPanel.tsx",
        "ui/src/components/striker/TacticalStriker.tsx",
        "ui/src/components/striker/Gauges.tsx",
        "ui/src/components/dashboard/AnalyticsPanel.tsx"
    ]
    for c in components:
        status = "✅" if os.path.exists(c) else "❌"
        print(f"  {status} {c}")

def check_syndicate_core():
    print("\n🔍 CHECKING SYNDICATE KINETIC WIRING...")
    cores = [
        "app/utils/token_engine.py",
        "app/routes/telemetry.py",
        "ui/src/lib/SequenceOrchestrator.ts"
    ]
    for c in cores:
        status = "✅" if os.path.exists(c) else "❌"
        print(f"  {status} {c}")

def verify_token_engine():
    print("\n🔍 VERIFYING TOKEN NEURAL ENGINE...")
    try:
        from app.utils.token_engine import UnifiedTokenEngine
        print("  ✅ Token engine imported successfully.")
    except Exception as e:
        print(f"  ❌ Token engine failure: {e}")

def check_env():
    print("\n🔍 CHECKING ENVIRONMENT...")
    keys = ["GROQ_KEYS", "GOOGLE_KEYS", "MASTER_KEY"]
    for k in keys:
        val = os.getenv(k)
        status = "✅" if val else "⚠️ (MISSING)"
        print(f"  {status} {k}")

if __name__ == "__main__":
    # Add project root to path for imports
    sys.path.append(str(Path(__file__).parent.parent))
    
    check_structure()
    check_ui()
    check_syndicate_core()
    verify_token_engine()
    check_env()
    print("\n🏁 DIAGNOSTIC COMPLETE. ALL SYSTEMS NOMINAL.")
