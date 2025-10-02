import json
import uuid
from langchain_core.messages import AIMessageChunk, AIMessage, ToolMessage, HumanMessage

from langgraph.graph.state import CompiledStateGraph

from typing import List

def generate_stream(graph: CompiledStateGraph, input_message: List[HumanMessage], conversation_id: str):
    # Generate unique message ID
    message_id = str(uuid.uuid4())
    
    # Send StartStep (f:) - Start of message processing
    yield f"f:{json.dumps({'messageId': message_id})}\n"
    
    tool_calls = {}
    current_message_tool_calls = []  # Track tool calls for the current message
    accumulated_text = ""
    token_count = 0

    try:
        for msg, metadata in graph.stream(
            {"messages": input_message},
            config={"configurable": {"thread_id": conversation_id}},
            stream_mode="messages",
        ):
            if isinstance(msg, ToolMessage):
                # Handle tool results - ToolCallResult (a:)
                tool_call_id = msg.tool_call_id
                yield f"a:{json.dumps({'toolCallId': tool_call_id, 'result': msg.content})}\n"

            elif isinstance(msg, AIMessageChunk) or isinstance(msg, AIMessage):
                # Handle text content - TextDelta (0:)
                if msg.content:
                    # Send text delta - properly escape the content
                    content = str(msg.content)
                    yield f"0:{json.dumps(content)}\n"
                    accumulated_text += content
                    token_count += len(content.split())

                # Handle tool calls - Reset current message tool calls and rebuild
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # Clear the current message tool calls list
                    current_message_tool_calls = []
                    
                    for tool_call in msg.tool_calls:
                        tool_call_id = tool_call.get('id', str(uuid.uuid4()))
                        tool_name = tool_call.get('name', '')

                        if tool_name != "":
                            # Add to current message tool calls list (maintains order)
                            current_message_tool_calls.append(tool_call_id)
                            
                            # Only initialize if this is a new tool call
                            if tool_call_id not in tool_calls:
                                tool_calls[tool_call_id] = {"name": tool_name, "args": ""}
                                
                                # Send StartToolCall (b:)
                                yield f"b:{json.dumps({'toolCallId': tool_call_id, 'toolName': tool_name})}\n"
                
                # Handle streaming tool call chunks
                if hasattr(msg, 'tool_call_chunks') and msg.tool_call_chunks:
                    for chunk in msg.tool_call_chunks:
                        args_chunk = chunk.get("args", "")
                        chunk_index = chunk.get("index", 0)
                        
                        # Use the current message's tool call list to map index to tool_call_id
                        tool_call_id = None
                        if chunk_index < len(current_message_tool_calls):
                            tool_call_id = current_message_tool_calls[chunk_index]
                        
                        # Accumulate args and send ToolCallArgsTextDelta (c:)
                        if tool_call_id and tool_call_id in tool_calls and args_chunk:
                            tool_calls[tool_call_id]["args"] += args_chunk
                            yield f"c:{json.dumps({'toolCallId': tool_call_id, 'argsTextDelta': args_chunk})}\n"
                        

        # Send FinishMessage (d:) with usage stats
        yield f"d:{json.dumps({'finishReason': 'stop', 'usage': {'promptTokens': token_count, 'completionTokens': token_count}})}\n"
        
    except Exception as e:
        # Send Error (3:)
        error_message = str(e)
        yield f"3:{json.dumps(error_message)}\n"