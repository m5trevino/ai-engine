import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from datetime import datetime

router = APIRouter()

async def telemetry_event_generator(request: Request):
    """
    Generates dummy and real telemetry events for the Live Wire.
    """
    initial_events = [
        {"time": datetime.now().isoformat(), "msg": "SYSTEM_HANDSHAKE_ESTABLISHED", "type": "success"},
        {"time": datetime.now().isoformat(), "msg": "LISTENING_ON_PRIMARY_MESH", "type": "info"},
    ]
    
    for event in initial_events:
        yield f"data: {json.json.dumps(event)}\n\n"

    while True:
        if await request.is_disconnected():
            break
        
        # In a real app, you'd pull from a queue or pub/sub
        # For now, we'll pulse the system status every 10s
        await asyncio.sleep(10)
        yield f"data: {json.json.dumps({'time': datetime.now().isoformat(), 'msg': 'HEARTBEAT_PULSE_STABLE', 'type': 'info'})}\n\n"

@router.get("/stream")
async def stream_telemetry(request: Request):
    return StreamingResponse(telemetry_event_generator(request), media_type="text/event-stream")
