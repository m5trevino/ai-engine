#!/usr/bin/env python3
"""
MIGRATE HERBERT V2 app_invariants → Peacock Unified (ENRICHMENT)

Problem: Herbert v2's dendritic_layer2_app_invariants has fuller text
(INVARIANT + SHADOW paragraphs) and code-analysis metadata (cyclomatic,
nesting, family, element, source_file) that Peacock Unified stripped.

Strategy:
  1. Load all v2 app_invariant docs
  2. Load all Unified app_invariant docs
  3. Match by invariant title (first line)
  4. For matches: update Unified doc with richer v2 text + merged metadata
  5. For unmatched: add as new doc

Usage:
    cd /root/hetzner/ai-engine && source .venv/bin/activate
    python app/scripts/migrate_herbert_v2_app_invariants.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

V2_PATH = "/root/hetzner/herbert/liquid-semiotic/dendritic/data/chroma_db"
UNIFIED_PATH = "/root/chroma-unified"


def extract_title(doc: str) -> str:
    """Extract invariant title for matching."""
    first_line = doc.strip().split("\n")[0]
    return first_line.replace("INVARIANT:", "").strip().lower()[:80]


def migrate(dry_run: bool = False):
    v2_client = chromadb.PersistentClient(path=V2_PATH)
    u_client = chromadb.PersistentClient(path=UNIFIED_PATH)

    v2_coll = v2_client.get_collection("dendritic_layer2_app_invariants")
    u_coll = u_client.get_collection("app_invariants")

    print(f"[INFO] Loading v2 app_invariants...")
    v2_data = v2_coll.get(include=["documents", "metadatas"])
    v2_by_title = {}
    for i, doc in enumerate(v2_data["documents"]):
        title = extract_title(doc)
        v2_by_title[title] = {
            "id": v2_data["ids"][i],
            "document": doc,
            "metadata": v2_data["metadatas"][i],
        }

    print(f"[INFO] Loading Unified app_invariants...")
    u_data = u_coll.get(include=["documents", "metadatas"])
    u_by_title = {}
    for i, doc in enumerate(u_data["documents"]):
        # Unified docs don't have INVARIANT: prefix, just the title
        title = doc.strip().split("\n")[0].strip().lower()[:80]
        u_by_title[title] = {
            "id": u_data["ids"][i],
            "document": doc,
            "metadata": u_data["metadatas"][i],
        }

    matched = 0
    enriched = 0
    unmatched = 0

    # Process matches: enrich Unified with v2 content + merged metadata
    update_ids = []
    update_docs = []
    update_metas = []

    add_ids = []
    add_docs = []
    add_metas = []

    for title, v2_item in v2_by_title.items():
        u_item = u_by_title.get(title)
        if u_item:
            matched += 1
            # Merge metadata: Unified has law_id, layer, version, source_repo
            # v2 has cyclomatic, nesting, family, element, source_file
            merged_meta = dict(u_item["metadata"])
            v2_meta = v2_item["metadata"]
            merged_meta["cyclomatic"] = v2_meta.get("cyclomatic", 0)
            merged_meta["nesting"] = v2_meta.get("nesting", 0)
            merged_meta["family"] = v2_meta.get("family", "")
            merged_meta["element"] = v2_meta.get("element", "")
            merged_meta["source_file"] = v2_meta.get("source_file", "")
            merged_meta["enriched_from_v2"] = True

            # Use the richer v2 document text
            rich_doc = v2_item["document"]

            if dry_run:
                enriched += 1
                continue

            update_ids.append(u_item["id"])
            update_docs.append(rich_doc)
            update_metas.append(merged_meta)
            enriched += 1
        else:
            unmatched += 1
            if dry_run:
                continue
            # Generate a new Unified-style ID
            new_id = f"app_invariants__{v2_item['id'].replace('layer2_', '')}"
            add_ids.append(new_id)
            add_docs.append(v2_item["document"])
            meta = dict(v2_item["metadata"])
            meta["layer"] = "layer2_app_invariants"
            meta["enriched_from_v2"] = True
            add_metas.append(meta)

    print(f"[INFO] Matched: {matched} | Unmatched: {unmatched} | To enrich: {enriched}")

    if dry_run:
        print("[DRY RUN] No changes made.")
        return

    # Batch update existing docs
    if update_ids:
        batch_size = 100
        for i in range(0, len(update_ids), batch_size):
            batch_i = update_ids[i:i+batch_size]
            batch_d = update_docs[i:i+batch_size]
            batch_m = update_metas[i:i+batch_size]
            u_coll.update(ids=batch_i, documents=batch_d, metadatas=batch_m)
            print(f"[UPDATE] Batch {i//batch_size + 1}: {len(batch_i)} docs enriched")

    # Batch add new docs
    if add_ids:
        batch_size = 100
        for i in range(0, len(add_ids), batch_size):
            batch_i = add_ids[i:i+batch_size]
            batch_d = add_docs[i:i+batch_size]
            batch_m = add_metas[i:i+batch_size]
            u_coll.add(ids=batch_i, documents=batch_d, metadatas=batch_m)
            print(f"[ADD] Batch {i//batch_size + 1}: {len(batch_i)} new docs")

    print(f"[DONE] Enriched {enriched} app_invariants in Peacock Unified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
