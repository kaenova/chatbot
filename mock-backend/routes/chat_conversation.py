import json

from utils.uuid import generate_uuid
from langchain_core.load import dumps
from langchain_core.messages.human import HumanMessage
from lib.auth import get_authenticated_user
from utils.stream_protocol import generate_stream
from utils.message_conversion import from_assistant_ui_contents_to_langgraph_contents

from typing import Annotated
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, Header, HTTPException

from agent.graph import graph
from lib.database import db_manager

class ChatRequest(BaseModel):
    messages: list

chat_conversation_route = APIRouter()

@chat_conversation_route.post("/chat")
async def chat_completions(request: ChatRequest, _: Annotated[str, Depends(get_authenticated_user)], userid:  Annotated[str | None, Header()] = None):
    """Chat completions endpoint."""

    if not userid:
        return {"error": "Missing userid header"}

    conversation_id = generate_uuid()

    # Convert the input message 
    if type(request.messages) is not list or len(request.messages) == 0:
        return {"error": "Invalid messages format"}
    
    last_message = request.messages[-1] if request.messages else ""
    last_message_langgraph_content = from_assistant_ui_contents_to_langgraph_contents(last_message['content'])
    input_message = [{
        "role": "user",
        "content": last_message_langgraph_content
    }]

    # Add user and the conversation id to the database
    db_manager.create_conversation(conversation_id, userid)

    return StreamingResponse(
        generate_stream(graph, input_message, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "text/plain; charset=utf-8",
            "Connection": "keep-alive",
            "x-vercel-ai-data-stream": "v1",
            "x-vercel-ai-ui-message-stream": "v1"
        }
    )


@chat_conversation_route.get("/last-conversation-id")
def get_last_conversation_id(_: Annotated[str, Depends(get_authenticated_user)], userid:  Annotated[str | None, Header()] = None):
    """Get last conversation ID endpoint."""
    if not userid:
        return {"error": "Missing userid header"}
    
    # Fetch the last conversation ID for the user from the database
    last_conversation_id = db_manager.get_last_conversation_id(userid)

    return {
        "userId": userid,
        "lastConversationId": last_conversation_id
    }

@chat_conversation_route.get("/conversations")
def get_conversations(_: Annotated[str, Depends(get_authenticated_user)], userid:  Annotated[str | None, Header()] = None):
    """Get conversations endpoint."""
    if not userid:
        return {"error": "Missing userid header"}

    # Fetch list of conversations for the user from the database
    conversations = db_manager.get_user_conversations(userid)
    
    # Convert to the expected API response format
    response = []
    for conv in conversations:
        # Get the first message from the conversation to use as title
        # For now, we'll use a default title since we don't store message content in metadata
        # In a real implementation, you might want to fetch the first message from LangGraph state
        conv_graph_val = graph.get_state(config={"configurable": {"thread_id": conv.id}}).values
        conv_graph_messages = conv_graph_val.get("messages", []) if conv_graph_val else []
        title = f"Conversations {conv.id[:8]}..."

        if conv_graph_messages:
            first_message = conv_graph_messages[0]
            content = first_message.content

            if isinstance(content, list) and len(content) > 0 and content[0]['type'] == 'text':
                title = content[0]['text']
            elif type(content) is str:
                title = content

        response.append({
            "id": conv.id,
            "title": title,
            "created_at": conv.created_at,
            "is_pinned": conv.is_pinned
        })
    
    return response

@chat_conversation_route.get("/conversations/{conversation_id}")
def get_chat_history(_: Annotated[str, Depends(get_authenticated_user)], userid:  Annotated[str | None, Header()] = None, conversation_id: str = ""):
    """Get chat history for a conversation."""
    if not userid:
        return {"error": "Missing userid header"}
    
    # Check if the conversation exists and belongs to the user
    if not db_manager.conversation_exists(conversation_id, userid):
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Fetch chat history for the conversation from LangGraph state
    try:
        # Get the conversation state from the checkpointer
        states_generator = graph.get_state_history(config={"configurable": {"thread_id": conversation_id}})
        states = list(states_generator)

        json_dumps = dumps(states)
        
        return json.loads(json_dumps)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")

@chat_conversation_route.post("/conversations/{conversation_id}/chat")
def chat_conversation(_: Annotated[str, Depends(get_authenticated_user)], userid: Annotated[str | None, Header()] = None, conversation_id: str = "", request: ChatRequest = None):
    """Chat in a specific conversation."""

    if not userid:
        return {"error": "Missing userid header"}
    
    if not request:
        return {"error": "Missing request body"}


    # Check if the conversation exists and belongs to the user
    if not db_manager.conversation_exists(conversation_id, userid):
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Convert the input message 
    if type(request.messages) is not list or len(request.messages) == 0:
        return {"error": "Invalid messages format"}
    
    last_message = request.messages[-1] if request.messages else ""
    last_message_langgraph_content = from_assistant_ui_contents_to_langgraph_contents(last_message['content'])
    input_message = [{
        "role": "user",
        "content": last_message_langgraph_content
    }]

    return StreamingResponse(
        generate_stream(graph, input_message, conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "text/plain; charset=utf-8",
            "Connection": "keep-alive",
            "x-vercel-ai-data-stream": "v1",
            "x-vercel-ai-ui-message-stream": "v1"
        }
    )
@chat_conversation_route.delete("/conversations/{conversation_id}")
def delete_conversation(_: Annotated[str, Depends(get_authenticated_user)], userid: Annotated[str | None, Header()] = None, conversation_id: str = ""):
    """Delete a conversation."""

    if not userid:
        return {"error": "Missing userid header"}

    # Delete the conversation from the database
    deleted = db_manager.delete_conversation(conversation_id, userid)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation deleted successfully"}

@chat_conversation_route.post("/conversations/{conversation_id}/pin")
def pin_conversation(_: Annotated[str, Depends(get_authenticated_user)], userid: Annotated[str | None, Header()] = None, conversation_id: str = ""):
    """Pin or unpin a conversation."""

    if not userid:
        return {"error": "Missing userid header"}
    
    existing_data = db_manager.get_conversation(conversation_id, userid)
    if not existing_data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Pin or unpin the conversation in the database
    updated = db_manager.pin_conversation(conversation_id, userid, not existing_data.is_pinned)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    action = "pinned" if updated else "unpinned"
    return {"message": f"Conversation {action} successfully"}
