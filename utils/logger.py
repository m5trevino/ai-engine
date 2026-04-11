"""
PEACOCK ENGINE - High-Signal Logger
Handles dual-track master logs, forensic vaulting, and unique tagging.
"""

import os
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Paths - dynamically find project root
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
VAULT_DIR = BASE_DIR / "vault"
SUCCESS_LOG = BASE_DIR / "success_strikes.log"
FAILED_LOG = BASE_DIR / "failed_strikes.log"
MANUAL_LOG = BASE_DIR / "manual_strikes.log"

# Settings (Can be overridden by env vars)
LOG_SUCCESS = os.getenv("LOG_SUCCESS", "true").lower() == "true"
LOG_FAILED = os.getenv("LOG_FAILED", "true").lower() == "true"

class HighSignalLogger:
    """Forensic logging system for Peacock Engine."""
    
    @staticmethod
    def generate_tag() -> str:
        """Generate a unique 8-character Tag ID."""
        return f"PEA-{uuid.uuid4().hex[:4].upper()}"

    @staticmethod
    def log_strike(
        gateway: str,
        model: str,
        prompt: str,
        response: str,
        usage: Dict[str, int],
        temp: float,
        cost: float,
        is_success: bool = True,
        is_manual: bool = False,
        error: Optional[str] = None
    ) -> str:
        """
        Log a strike to the master log and verbatim vault.
        Returns the unique Tag ID.
        """
        tag = HighSignalLogger.generate_tag()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Determine Vault Destination
        vault_subdir = "successful" if is_success else "failed"
        target_dir = VAULT_DIR / vault_subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        vault_file = target_dir / f"{tag}.txt"
        
        # 2. Prepare Verbatim Content
        verbatim_content = f"""TAG: {tag}
TIMESTAMP: {timestamp}
GATEWAY: {gateway.upper()}
MODEL: {model}
TEMP: {temp}
STATUS: {"SUCCESS" if is_success else "FAILED"}
COST: ${cost:.6f}
PROMPT_TOKENS: {usage.get('prompt_tokens', 0)}
COMPLETION_TOKENS: {usage.get('completion_tokens', 0)}
TOTAL_TOKENS: {usage.get('total_tokens', 0)}
{f"ERROR: {error}" if error else ""}

--- VERBATIM PROMPT ---
{prompt}

--- VERBATIM RESPONSE ---
{response}
"""
        
        # 3. Save to Vault (if enabled)
        if (is_success and LOG_SUCCESS) or (not is_success and LOG_FAILED):
            vault_file.write_text(verbatim_content)
            
        # 4. Update Master Logs
        master_log = SUCCESS_LOG if is_success else FAILED_LOG
        log_entry = f"[{timestamp}] {tag} | {gateway.upper().ljust(8)} | {model.ljust(25)} | TMP:{temp} | {usage.get('total_tokens', 0):>6}T | ${cost:.6f}\n"
        
        with open(master_log, "a") as f:
            f.write(log_entry)
            
        # 5. Handle Manual Strike Log
        if is_manual:
            with open(MANUAL_LOG, "a") as f:
                f.write(log_entry)
                
        return tag

    @staticmethod
    def error(message: str):
        """Log a system error to the failure log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tag = HighSignalLogger.generate_tag()
        log_entry = f"[{timestamp}] {tag} | ERROR    | {message}\n"
        with open(FAILED_LOG, "a") as f:
            f.write(log_entry)
        # Console output for visibility during development
        print(f"\033[1;31m[✗] {log_entry.strip()}\033[0m")

    @staticmethod
    def get_log_status() -> Dict[str, bool]:
        """Return the current ON/OFF status of logs."""
        return {
            "success_logging": LOG_SUCCESS,
            "failed_logging": LOG_FAILED
        }
