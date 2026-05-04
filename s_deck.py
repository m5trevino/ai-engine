#!/usr/bin/env python3
"""
SYNDICATE PAYLOAD DECK (s_deck.py)
Headless Refinery Command Center
"""

import os
import sys
import json
import asyncio
import httpx
from pathlib import Path
from typing import List, Optional

API_BASE = "http://localhost:3099"

class SyndicateCLI:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=300.0)

    async def start_mission(self, prompt_path: str, file_paths: List[str], model: str):
        """Initialize a mission via the refinery API."""
        payload = {
            "name": f"CLI_STRIKE_{int(asyncio.get_event_loop().time())}",
            "prompt_path": str(Path(prompt_path).resolve()),
            "file_paths": [str(Path(p).resolve()) for p in file_paths],
            "model_id": model,
            "settings": {
                "temperature": 0.3,
                "max_tokens": 4096
            }
        }
        
        try:
            res = await self.client.post(f"{API_BASE}/v1/payloads/strike", json=payload)
            res.raise_for_status()
            data = res.json()
            batch_id = data.get("batch_id")
            print(f"[⚡] MISSION_INITIATED | ID: {batch_id} | UNITS: {data.get('items')}")
            return batch_id
        except Exception as e:
            print(f"[!] MISSION_FAILURE: {e}")
            return None

    async def stream_mission(self, batch_id: str):
        """Connect to the Live Wire SSE stream and display progress."""
        print(f"[LIVE] CONNECTING_TO_WIRE_{batch_id}...")
        
        async with self.client.stream("GET", f"{API_BASE}/v1/payloads/stream/{batch_id}") as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        self._handle_event(data)
                        if data.get("type") == "mission_complete":
                            break
                    except:
                        pass
                elif line.strip() == "":
                    continue

    def _handle_event(self, event: dict):
        etype = event.get("type")
        if etype == "system":
            print(f"[{etype.upper()}] {event.get('content')}")
        elif etype == "item_start":
            print(f"\n[STRIKE] ➢ {event.get('file')}")
        elif etype == "item_chunk":
            # Print without newline for streaming effect? 
            # might be too messy for CLI if many files run at once
            pass
        elif etype == "item_done":
            meta = event.get("metadata", {})
            usage = meta.get("usage", {})
            print(f"[HIT]   ✓ COMPLETE | TOKENS: {usage.get('total_tokens')} | COST: ${meta.get('cost')}")
        elif etype == "mission_complete":
            print(f"\n[FIN] MISSION_SUCCESSFUL_SYNDICATE_OUT")

async def main():
    if len(sys.argv) < 4:
        print("USAGE: s_deck.py <prompt_path> <model_id> <file1> <file2> ...")
        sys.exit(1)

    prompt = sys.argv[1]
    model = sys.argv[2]
    files = sys.argv[3:]

    cli = SyndicateCLI()
    batch_id = await cli.start_mission(prompt, files, model)
    if batch_id:
        await cli.stream_mission(batch_id)
    await cli.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
