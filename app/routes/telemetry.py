import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from datetime import datetime

from app.monitoring.metrics import global_metrics

router = APIRouter()

async def telemetry_event_generator(request: Request):
    """
    Generates high-fidelity telemetry pulse for the Syndicate HUD.
    """
    # Initial Handshake
    yield f"data: {json.dumps({'time': datetime.now().isoformat(), 'msg': 'SYNDICATE_HANDSHAKE_ESTABLISHED', 'type': 'success'})}\n\n"
    await asyncio.sleep(0.5)

    while True:
        if await request.is_disconnected():
            break
        
        # Pull pulse from global metrics
        stats = global_metrics.get_realtime_stats()
        
        # Package for HUD
        payload = {
            "time": datetime.now().isoformat(),
            "rpm": stats["rpm"],
            "tps": stats["tps"],
            "tokens": stats["tokens"],
            "cost": stats["cost"],
            "success_rate": stats["success_rate"],
            "msg": "PULSE_STABLE",
            "type": "telemetry"
        }
        
        yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(0.5) # 2Hz fidelity

@router.get("/stream")
async def stream_telemetry(request: Request):
    return StreamingResponse(telemetry_event_generator(request), media_type="text/event-stream")
