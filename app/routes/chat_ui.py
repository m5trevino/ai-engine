"""
PEACOCK ENGINE - Chat UI Routes
API endpoints for the web chat interface.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.db.database import ConversationDB
from app.utils.formatter import CLIFormatter

router = APIRouter()


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    model_id: str
    key_account: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    tokens_used: int
    model_id: Optional[str]
    key_account: Optional[str]
    timestamp: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    model_id: str
    key_account: Optional[str]
    created_at: str
    updated_at: str


@router.get("/conversations")
async def get_conversations(limit: int = 50):
    """Get all conversations."""
    try:
        conversations = ConversationDB.get_conversations(limit)
        return conversations
    except Exception as e:
        CLIFormatter.error(f"Failed to get conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations")
async def create_conversation(data: ConversationCreate):
    """Create a new conversation."""
    try:
        conv_id = ConversationDB.create(
            title=data.title,
            model_id=data.model_id,
            key_account=data.key_account
        )
        return {"id": conv_id, "status": "created"}
    except Exception as e:
        CLIFormatter.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Get a specific conversation."""
    try:
        conversations = ConversationDB.get_conversations(limit=1000)
        conversation = next((c for c in conversations if c['id'] == conv_id), None)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        CLIFormatter.error(f"Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str):
    """Get all messages for a conversation."""
    try:
        conversation = await get_conversation(conv_id)
        messages = ConversationDB.get_messages(conv_id)
        
        return {
            "conversation": conversation,
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        CLIFormatter.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    try:
        ConversationDB.delete_conversation(conv_id)
        return {"status": "deleted"}
    except Exception as e:
        CLIFormatter.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
