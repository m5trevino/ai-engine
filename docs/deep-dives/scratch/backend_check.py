import os
import sys
from pathlib import Path

# Adjust path to include the project root
project_root = "/home/flintx/peacock-engine"
sys.path.insert(0, project_root)

# Try to import from the production-style token_counter
try:
    from app.utils.token_counter import count_tokens
    from app.utils.logger import HighSignalLogger
    
    print("[✓] Imports successful.")
    
    # Test 1: Logger.error method existence
    if hasattr(HighSignalLogger, "error"):
        print("[✓] HighSignalLogger.error method exists.")
        # Test 2: Actually log an error
        try:
            HighSignalLogger.error("TEST_HARDENING_SYNDICATE")
            print("[✓] Logger.error executed successfully.")
        except Exception as e:
            print(f"[✗] Logger.error failed: {e}")
    else:
        print("[✗] HighSignalLogger.error method MISSING.")

    # Test 3: Token counter functionality
    try:
        count = count_tokens("Test prompt", provider="google")
        print(f"[✓] Token counting successful: {count} tokens.")
    except Exception as e:
        print(f"[✗] Token counting failed: {e}")

except ImportError as e:
    print(f"[✗] Module Import Failed: {e}")
except Exception as e:
    print(f"[✗] Unexpected Error: {e}")
