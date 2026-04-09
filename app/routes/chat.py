"""
PEACOCK ENGINE - Generic Chat Endpoint
A unified, CLI-friendly endpoint for chatting with any model.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from pathlib import Path
import time

from app.core.striker import execute_strike, execute_streaming_strike
from app.config import MODEL_REGISTRY
from app.utils.formatter import CLIFormatter
from app.db.database import ConversationDB
from fastapi.responses import StreamingResponse
import json

router = APIRouter()


class ChatRequest(BaseModel):
    """Generic chat request model."""
    model: str = Field(..., description="Model ID from the registry (e.g., 'gemini-2.0-flash-lite')")
    timeout: Optional[int] = Field(default=None, description="Timeout in seconds for this request")
    title: Optional[str] = Field(default=None, description="Clean title for the conversation")
    prompt: str = Field(..., description="The prompt text")
    files: Optional[List[str]] = Field(default=None, description="Optional list of file paths to include as context")
    format: Literal["text", "json", "pydantic"] = Field(default="text", description="Output format")
    schema_definition: Optional[Dict[str, Any]] = Field(default=None, alias="schema", description="Schema definition for 'pydantic' format")
    temp: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for generation (Compatibility shorthand)")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Temperature for generation")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Nucleus sampling threshold")
    top_k: Optional[int] = Field(default=None, ge=0, description="Top-K sampling")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    seed: Optional[int] = Field(default=None, description="Deterministic seed")
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Presence penalty")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Frequency penalty")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")
    key: Optional[str] = Field(default=None, description="Optional: specific key account to use")


class ChatResponse(BaseModel):
    """Generic chat response model."""
    content: Any
    model: str
    gateway: str
    key_used: str
    format: str
    usage: Dict[str, int]
    duration_ms: int


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Generic chat endpoint - works with any model from any gateway.
    
    Features:
    - Any model from the registry
    - File payload injection
    - Multiple output formats (text, json, pydantic)
    - Optional specific key selection
    
    Examples:
    ```json
    // Simple text request
    {
      "model": "gemini-2.0-flash-lite",
      "prompt": "Hello, how are you?"
    }
    
    // With file context
    {
      "model": "llama-3.1-8b-instant",
      "prompt": "Explain this code",
      "files": ["/home/flintx/myproject/main.py"]
    }
    
    // JSON output format
    {
      "model": "gemini-2.0-flash-lite",
      "prompt": "Extract info from this text",
      "format": "json"
    }
    
    // Pydantic format with custom schema
    {
      "model": "gemini-2.0-flash-lite",
      "prompt": "Analyze this code",
      "format": "pydantic",
      "schema": {
        "name": "CodeAnalysis",
        "fields": [
          {"name": "language", "type": "str"},
          {"name": "complexity", "type": "int"}
        ]
      }
    }
    ```
    """
    start_time = time.time()
    
    # Find model config
    model_config = next((m for m in MODEL_REGISTRY if m.id == request.model), None)
    if not model_config:
        available = [m.id for m in MODEL_REGISTRY]
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown model '{request.model}'. Available: {available}"
        )
    
    # Build prompt with file context if provided
    final_prompt = request.prompt
    if request.files:
        file_contexts = []
        for file_path in request.files:
            path = Path(file_path)
            if path.exists():
                try:
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    file_contexts.append(f"\n\n--- FILE: {file_path} ---\n{content}")
                except Exception as e:
                    CLIFormatter.warning(f"Failed to read {file_path}: {e}")
            else:
                CLIFormatter.warning(f"File not found: {file_path}")
        
        if file_contexts:
            final_prompt = f"{request.prompt}\n\nCONTEXT:{''.join(file_contexts)}"
    
    # Determine format mode for striker
    format_mode = None
    if request.format == "pydantic":
        format_mode = "pydantic"
    elif request.format == "json":
        format_mode = "json"
    
    try:
        # Collect advanced generation parameters
        gen_params = {
            "temperature": request.temperature if request.temperature is not None else request.temp,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "max_tokens": request.max_tokens,
            "seed": request.seed,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty,
            "stop_sequences": request.stop,
        }

        # If specific key requested, use precision strike
        if request.key:
            from app.core.striker import execute_precision_strike
            result = await execute_precision_strike(
                gateway=model_config.gateway,
                model_id=request.model,
                prompt=final_prompt,
                target_account=request.key,
                is_manual=False,
                timeout=request.timeout,
                **gen_params
            )
        else:
            # Regular strike
            result = await execute_strike(
                gateway=model_config.gateway,
                model_id=request.model,
                prompt=final_prompt,
                format_mode=format_mode,
                dynamic_schema=request.schema if request.format == "pydantic" else None,
                is_manual=False,
                timeout=request.timeout,
                **gen_params
            )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # All info now returned in consistent result dict from execute_strike
        content = result.get("content")
        usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        key_used = result.get("keyUsed", "unknown")
        tag = result.get("tag", "N/A")
        cost = result.get("cost", 0.0)
        
        # If JSON format requested but content is string, try to parse
        if request.format == "json" and isinstance(content, str):
            import json
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                # Return as-is if not valid JSON
                pass
        
        # Save to database (create conversation if new, add messages)
        try:
            # Generate a conversation ID based on model and timestamp if needed
            import uuid
            conv_id = str(uuid.uuid4())[:8]
            
            # Create conversation
            ConversationDB.create(
                title=request.title or (request.prompt[:50] + "..." if len(request.prompt) > 50 else request.prompt),
                model_id=request.model,
                key_account=key_used
            )
            
            # Add messages (both user and assistant)
            ConversationDB.add_message(
                conv_id=conv_id,
                role='user',
                content=request.prompt,
                model_id=request.model,
                key_account=key_used
            )
            
            response_content = content if isinstance(content, str) else str(content)
            ConversationDB.add_message(
                conv_id=conv_id,
                role='assistant',
                content=response_content,
                tokens_used=usage.get('total_tokens', 0),
                prompt_tokens=usage.get('prompt_tokens', 0),
                completion_tokens=usage.get('completion_tokens', 0),
                model_id=request.model,
                key_account=key_used
            )
        except Exception as e:
            # Don't fail the request if DB save fails
            CLIFormatter.warning(f"Failed to save conversation: {e}")
        
        return ChatResponse(
            content=content,
            model=request.model,
            gateway=model_config.gateway,
            key_used=key_used,
            format=request.format,
            usage=usage,
            duration_ms=duration_ms
        )
        
    except Exception as e:
        CLIFormatter.error(f"Chat Strike Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events (SSE).
    """
    model_config = next((m for m in MODEL_REGISTRY if m.id == request.model), None)
    if not model_config:
        raise HTTPException(status_code=400, detail=f"Unknown model: {request.model}")

    async def event_generator():
        try:
            async for chunk in execute_streaming_strike(
                gateway=model_config.gateway,
                model_id=request.model,
                prompt=request.prompt,
                timeout=request.timeout,
                files=request.files,
                temperature=request.temperature if request.temperature is not None else request.temp,
                top_p=request.top_p,
                top_k=request.top_k,
                max_tokens=request.max_tokens,
                seed=request.seed,
                presence_penalty=request.presence_penalty,
                frequency_penalty=request.frequency_penalty,
                stop_sequences=request.stop
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/models")
async def get_available_models():
    """Get all available models grouped by gateway."""
    by_gateway = {}
    for model in MODEL_REGISTRY:
        gw = model.gateway
        if gw not in by_gateway:
            by_gateway[gw] = []
        by_gateway[gw].append({
            "id": model.id,
            "tier": model.tier,
            "note": model.note,
            "rpm": model.rpm,
            "tpm": model.tpm,
            "rpd": model.rpd
        })
    return by_gateway


@router.get("/models/{gateway}")
async def get_gateway_models(gateway: str):
    """Get models for a specific gateway."""
    gateway_lower = gateway.lower()
    models = [m for m in MODEL_REGISTRY if m.gateway == gateway_lower]
    
    if not models:
        raise HTTPException(status_code=404, detail=f"No models found for gateway: {gateway}")
    
    return [
        {
            "id": m.id,
            "tier": m.tier,
            "note": m.note,
            "rpm": m.rpm,
            "tpm": m.tpm,
            "rpd": m.rpd
        }
        for m in models
    ]
@router.websocket("/ws/ws")
async def chat_ws(websocket: WebSocket):
    """
    Bidirectional WebSocket for real-time streaming.
    Protocol:
    1. Connect
    2. Receive 'config' {model, temp, files}
    3. Loop:
       - Receive 'prompt' {content}
       - Stream 'content' chunks
       - Send 'metadata' {usage}
    """
    await websocket.accept()
    CLIFormatter.info("Neural Link Established (WebSocket)")
    
    # Session state
    config = {
        "model": "gemini-2.0-flash-lite",
        "temp": 0.7,
        "files": []
    }
    
    try:
        while True:
            # Wait for message from client
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")
            
            if msg_type == "config":
                config.update({
                    "model": data.get("model", config["model"]),
                    "temp": data.get("temp", config["temp"]),
                    "files": data.get("files", config["files"])
                })
                await websocket.send_json({"type": "info", "content": f"CONFIG_SYNC: {config['model']}"})
                
            elif msg_type == "prompt":
                prompt = data.get("content")
                if not prompt:
                    continue
                
                model_id = config["model"]
                model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
                if not model_cfg:
                    await websocket.send_json({"type": "error", "content": f"Unknown model: {model_id}"})
                    continue
                
                # Start streaming strike
                try:
                    full_content = ""
                    async for chunk in execute_streaming_strike(
                        gateway=model_cfg.gateway,
                        model_id=model_id,
                        prompt=prompt,
                        temp=config["temp"],
                        files=config["files"],
                        is_manual=False
                    ):
                        if "content" in chunk:
                            content = chunk["content"]
                            full_content += content
                            await websocket.send_json({"type": "content", "content": content})
                        elif "error" in chunk:
                            await websocket.send_json({"type": "error", "content": chunk["error"]})
                    
                    # Send completion metadata
                    # Note: execute_streaming_strike in V3 often doesn't return full usage in the generator, 
                    # so we estimate or provide what we have.
                    await websocket.send_json({
                        "type": "metadata",
                        "usage": {
                            "prompt_tokens": len(prompt.split()), 
                            "completion_tokens": len(full_content.split()),
                            "total_tokens": len(prompt.split()) + len(full_content.split())
                        }
                    })
                    
                except Exception as e:
                    CLIFormatter.error(f"WS Strike Failure: {e}")
                    await websocket.send_json({"type": "error", "content": str(e)})
            
    except WebSocketDisconnect:
        CLIFormatter.info("Neural Link Severed (Websocket)")
    except Exception as e:
        CLIFormatter.error(f"WebSocket Error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass
