#!/usr/bin/env python3
"""
INGEST CONVERSATION TURN LOGS → Peacock Unified chat_conversations

Reads .md turn logs from /logs/conversations/ and upserts them into
the chat_conversations collection via Peacock Unified API.

Usage:
    cd /root/hetzner/ai-engine && source .venv/bin/activate
    python app/scripts/ingest_conversation_logs.py [--dry-run]
"""

import os
import sys
import yaml
import argparse
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

PEACOCK_UNIFIED_URL = os.getenv("PEACOCK_UNIFIED_URL", "http://localhost:8000")
LOGS_PATH = Path(__file__).parent.parent.parent.resolve() / "logs" / "conversations"
COLLECTION_NAME = "chat_conversations"


def parse_turn_file(path: Path) -> dict:
    """Parse a single .md turn log into structured data."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        meta = yaml.safe_load(parts[1])
    except Exception:
        return None

    body = parts[2].strip()
    return {
        "conversation_id": meta.get("conversation_id", ""),
        "turn": meta.get("turn", 0),
        "timestamp": meta.get("timestamp", ""),
        "model": meta.get("model", ""),
        "mode": meta.get("mode", ""),
        "gateway": meta.get("gateway", ""),
        "key_account": meta.get("key_account", ""),
        "cost": meta.get("cost", 0.0),
        "latency_ms": meta.get("latency_ms", 0),
        "platform": meta.get("platform", "PEACOCK"),
        "project": meta.get("project", "unknown"),
        "has_code_blocks": meta.get("has_code_blocks", "false"),
        "body": body,
        "source_file": str(path),
    }


def check_exists(doc_id: str) -> bool:
    """Check if a document already exists in the collection."""
    try:
        resp = httpx.get(
            f"{PEACOCK_UNIFIED_URL}/api/document/{COLLECTION_NAME}/{doc_id}",
            timeout=10.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def upsert_document(doc_id: str, document: str, metadata: dict) -> bool:
    """Upsert a single document via Peacock Unified API."""
    try:
        resp = httpx.post(
            f"{PEACOCK_UNIFIED_URL}/api/collections/{COLLECTION_NAME}/add",
            json={"ids": [doc_id], "documents": [document], "metadatas": [metadata]},
            timeout=30.0,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[ERROR] API error for {doc_id}: {e}")
        return False


def ingest_turns(dry_run: bool = False):
    logs_path = Path(LOGS_PATH)
    if not logs_path.exists():
        print(f"[ERROR] Logs path not found: {logs_path}")
        return

    md_files = list(logs_path.rglob("*.md"))
    if not md_files:
        print("[INFO] No .md turn logs found.")
        return

    print(f"[INFO] Found {len(md_files)} turn log files")

    if dry_run:
        print("[DRY RUN] Would parse and upsert the following:")

    ingested = 0
    skipped = 0
    errors = 0

    for path in md_files:
        turn = parse_turn_file(path)
        if not turn:
            errors += 1
            continue

        conv_id = turn["conversation_id"]
        turn_num = turn["turn"]
        if not conv_id or not turn_num:
            errors += 1
            continue

        doc_id = f"{conv_id}_turn_{turn_num:03d}"

        if not dry_run and check_exists(doc_id):
            skipped += 1
            continue

        metadata = {
            "conversation_id": conv_id,
            "turn": turn_num,
            "timestamp": str(turn["timestamp"])[:10] if turn["timestamp"] else "",
            "model": turn["model"] or "unknown",
            "mode": turn["mode"] or "raw",
            "gateway": turn["gateway"] or "unknown",
            "key_account": turn["key_account"] or "unknown",
            "cost": float(turn["cost"] or 0),
            "latency_ms": int(turn["latency_ms"] or 0),
            "platform": turn["platform"] or "PEACOCK",
            "project": turn["project"] or "unknown",
            "has_code_blocks": str(turn["has_code_blocks"]).lower(),
            "vault": "chat_conversations",
            "entry": str(turn_num).zfill(3),
            "source_file": str(path),
        }

        document = turn["body"]

        if dry_run:
            print(f"  [DRY] {doc_id} | {turn['model']} | {turn['mode']} | {len(document)} chars")
            ingested += 1
            continue

        if upsert_document(doc_id, document, metadata):
            ingested += 1
        else:
            errors += 1

    print(f"[DONE] Ingested: {ingested} | Skipped (already exists): {skipped} | Errors: {errors}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest conversation turn logs into Peacock Unified")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    args = parser.parse_args()
    ingest_turns(dry_run=args.dry_run)
