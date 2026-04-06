"""
Enhanced Chat API for WebUI
Supports: streaming, conversation history, file uploads, multi-turn
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, AsyncGenerator
from datetime import datetime
import json
import asyncio
import time
from pathlib import Path

from app.config import MODEL_REGISTRY
from app.core.key_manager import GooglePool, GroqPool, DeepSeekPool, MistralPool

router = APIRouter()

# Simple in-memory conversation store (replace with DB in production)
conversations: Dict[str, dict] = {}


class Message(BaseModel):
    """Chat message."""
    role: str = Field(..., description="system, user, or assistant")
    content: str
    timestamp: Optional[float] = None
    files: Optional[List[str]] = None


class Conversation(BaseModel):
    """Conversation thread."""
    id: str
    title: str
    model: str
    messages: List[Message]
    created_at: float
    updated_at: float
    token_count: int = 0


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None
    files: Optional[List[str]] = None
    stream: bool = True
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    message: Message
    conversation_id: str
    model: str
    usage: Dict
    duration_ms: float


class ConversationListItem(BaseModel):
    """Conversation list item."""
    id: str
    title: str
    model: str
    message_count: int
    updated_at: float
    preview: str


@router.post("/conversations")
async def create_conversation(model: str, title: Optional[str] = None):
    """Create a new conversation."""
    import uuid
    
    # Validate model
    m = next((m for m in MODEL_REGISTRY if m.id == model), None)
    if not m:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    
    conv_id = str(uuid.uuid4())[:8]
    now = time.time()
    
    conversations[conv_id] = {
        "id": conv_id,
        "title": title or f"Chat {conv_id}",
        "model": model,
        "messages": [],
        "created_at": now,
        "updated_at": now,
        "token_count": 0
    }
    
    return {"conversation_id": conv_id, "model": model}


@router.get("/conversations", response_model=List[ConversationListItem])
async def list_conversations(limit: int = 20, offset: int = 0):
    """List recent conversations."""
    sorted_convs = sorted(
        conversations.values(),
        key=lambda x: x["updated_at"],
        reverse=True
    )[offset:offset + limit]
    
    result = []
    for c in sorted_convs:
        preview = ""
        if c["messages"]:
            last_msg = c["messages"][-1]
            preview = last_msg["content"][:100] + "..." if len(last_msg["content"]) > 100 else last_msg["content"]
        
        result.append(ConversationListItem(
            id=c["id"],
            title=c["title"],
            model=c["model"],
            message_count=len(c["messages"]),
            updated_at=c["updated_at"],
            preview=preview
        ))
    
    return result


@router.get("/conversations/{conv_id}", response_model=Conversation)
async def get_conversation(conv_id: str):
    """Get a conversation with full history."""
    if conv_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    c = conversations[conv_id]
    return Conversation(
        id=c["id"],
        title=c["title"],
        model=c["model"],
        messages=[Message(**m) for m in c["messages"]],
        created_at=c["created_at"],
        updated_at=c["updated_at"],
        token_count=c["token_count"]
    )


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    if conv_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del conversations[conv_id]
    return {"message": f"Conversation {conv_id} deleted"}


@router.post("/conversations/{conv_id}/title")
async def update_conversation_title(conv_id: str, title: str):
    """Update conversation title."""
    if conv_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversations[conv_id]["title"] = title
    conversations[conv_id]["updated_at"] = time.time()
    
    return {"message": "Title updated", "title": title}


async def generate_chat_stream(
    conv_id: str,
    user_message: str,
    model: str,
    files: Optional[List[str]],
    temperature: float,
    max_tokens: Optional[int]
) -> AsyncGenerator[str, None]:
    """Generate streaming chat response."""
    
    conv = conversations.get(conv_id)
    if not conv:
        yield f"data: {json.dumps({'error': 'Conversation not found'})}\n\n"
        return
    
    # Add user message
    user_msg = {
        "role": "user",
        "content": user_message,
        "timestamp": time.time(),
        "files": files
    }
    conv["messages"].append(user_msg)
    
    # Build context from history
    context = ""
    for msg in conv["messages"][-10:]:  # Last 10 messages for context
        prefix = "User: " if msg["role"] == "user" else "Assistant: "
        context += f"{prefix}{msg['content']}\n\n"
    
    # Include file contents if provided
    file_context = ""
    if files:
        for f in files:
            try:
                content = Path(f).read_text(encoding='utf-8', errors='ignore')
                file_context += f"\n--- File: {f} ---\n{content[:5000]}\n---\n"
            except:
                pass
    
    full_prompt = f"{file_context}\n\nPrevious conversation:\n{context}\n\nUser: {user_message}\n\nAssistant:"
    
    # Determine gateway
    m = next((m for m in MODEL_REGISTRY if m.id == model), None)
    if not m:
        yield f"data: {json.dumps({'error': f'Unknown model: {model}'})}\n\n"
        return
    
    gateway = m.gateway
    
    # Start streaming
    start_time = time.time()
    assistant_content = ""
    
    try:
        from app.core.striker import execute_streaming_strike
        
        # Send start event
        yield f"data: {json.dumps({'event': 'start', 'model': model})}\n\n"
        
        # Stream the response
        async for chunk in execute_streaming_strike(
            gateway=gateway,
            model_id=model,
            prompt=full_prompt,
            temp=temperature,
            is_manual=False
        ):
            if "content" in chunk:
                content = chunk["content"]
                assistant_content += content
                yield f"data: {json.dumps({'event': 'token', 'content': content})}\n\n"
            elif "error" in chunk:
                yield f"data: {json.dumps({'event': 'error', 'error': chunk['error']})}\n\n"
                return
        
        # Add assistant message to conversation
        assistant_msg = {
            "role": "assistant",
            "content": assistant_content,
            "timestamp": time.time()
        }
        conv["messages"].append(assistant_msg)
        conv["updated_at"] = time.time()
        
        # Estimate tokens
        token_count = len(full_prompt.split()) + len(assistant_content.split())
        conv["token_count"] += token_count
        
        # Send done event
        duration = (time.time() - start_time) * 1000
        done_data = {
            'event': 'done',
            'duration_ms': duration,
            'usage': {'total_tokens': token_count}
        }
        yield f"data: {json.dumps(done_data)}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response using SSE."""
    
    # Get or create conversation
    conv_id = request.conversation_id
    if not conv_id:
        import uuid
        conv_id = str(uuid.uuid4())[:8]
        model = request.model or "gemini-2.0-flash-lite"
        conversations[conv_id] = {
            "id": conv_id,
            "title": request.message[:30] + "..." if len(request.message) > 30 else request.message,
            "model": model,
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "token_count": 0
        }
    else:
        if conv_id not in conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        model = request.model or conversations[conv_id]["model"]
    
    return StreamingResponse(
        generate_chat_stream(
            conv_id=conv_id,
            user_message=request.message,
            model=model,
            files=request.files,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-ID": conv_id
        }
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_non_stream(request: ChatRequest):
    """Non-streaming chat endpoint."""
    
    # Get or create conversation
    conv_id = request.conversation_id
    if not conv_id:
        import uuid
        conv_id = str(uuid.uuid4())[:8]
        model = request.model or "gemini-2.0-flash-lite"
        conversations[conv_id] = {
            "id": conv_id,
            "title": request.message[:30] + "...",
            "model": model,
            "messages": [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "token_count": 0
        }
    else:
        if conv_id not in conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        model = request.model or conversations[conv_id]["model"]
    
    conv = conversations[conv_id]
    
    # Add user message
    user_msg = {
        "role": "user",
        "content": request.message,
        "timestamp": time.time(),
        "files": request.files
    }
    conv["messages"].append(user_msg)
    
    # Build context
    context = ""
    for msg in conv["messages"][-10:]:
        prefix = "User: " if msg["role"] == "user" else "Assistant: "
        context += f"{prefix}{msg['content']}\n\n"
    
    file_context = ""
    if request.files:
        for f in request.files:
            try:
                content = Path(f).read_text(encoding='utf-8', errors='ignore')
                file_context += f"\n--- File: {f} ---\n{content[:5000]}\n---\n"
            except:
                pass
    
    full_prompt = f"{file_context}\n\nPrevious conversation:\n{context}\n\nUser: {request.message}\n\nAssistant:"
    
    # Determine gateway and execute
    m = next((m for m in MODEL_REGISTRY if m.id == model), None)
    if not m:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    
    start = time.time()
    
    try:
        from app.core.striker import execute_strike
        result = await execute_strike(
            gateway=m.gateway,
            model_id=model,
            prompt=full_prompt,
            temp=request.temperature,
            is_manual=False
        )
        
        content = result.get("content", "")
        duration = (time.time() - start) * 1000
        
        # Add assistant message
        assistant_msg = {
            "role": "assistant",
            "content": content,
            "timestamp": time.time()
        }
        conv["messages"].append(assistant_msg)
        conv["updated_at"] = time.time()
        
        usage = result.get("usage", {"total_tokens": len(full_prompt.split()) + len(content.split())})
        
        return ChatResponse(
            message=Message(**assistant_msg),
            conversation_id=conv_id,
            model=model,
            usage=usage,
            duration_ms=duration
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for use in chat."""
    
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    # Save file with unique name
    import uuid
    file_id = str(uuid.uuid4())[:8]
    file_path = upload_dir / f"{file_id}_{file.filename}"
    
    content = await file.read()
    file_path.write_bytes(content)
    
    return {
        "file_id": file_id,
        "filename": file.filename,
        "path": str(file_path),
        "size": len(content)
    }


@router.get("/models/available")
async def get_available_chat_models():
    """Get list of models available for chat (non-frozen)."""
    models = []
    for m in MODEL_REGISTRY:
        if m.status == "active":
            models.append({
                "id": m.id,
                "gateway": m.gateway,
                "tier": m.tier,
                "rpm": m.rpm,
                "tpm": m.tpm,
                "context_window": m.context_window
            })
    return {"models": models}


@router.post("/conversations/{conv_id}/clear")
async def clear_conversation_history(conv_id: str):
    """Clear all messages from a conversation."""
    if conv_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversations[conv_id]["messages"] = []
    conversations[conv_id]["token_count"] = 0
    conversations[conv_id]["updated_at"] = time.time()
    
    return {"message": "Conversation history cleared"}
