import json
import uuid
from langchain_core.messages import AIMessageChunk, AIMessage, ToolMessage, HumanMessage

from langgraph.graph.state import CompiledStateGraph

from typing import List

async def generate_stream(graph: CompiledStateGraph, input_message: List[HumanMessage], conversation_id: str):
    # Generate unique message ID
    message_id = str(uuid.uuid4())
    
    # Send StartStep (f:) - Start of message processing
    yield f"f:{json.dumps({'messageId': message_id})}\n"
    
    tool_calls = {}
    tool_calls_by_idx = {}
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

                # Handle tool calls
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_call_id = tool_call.get('id', str(uuid.uuid4()))
                        tool_name = tool_call.get('name', '')

                        if tool_name == "":
                            continue

                        tool_calls_by_idx[len(tool_calls_by_idx)] = tool_call_id
                        tool_calls[tool_call_id] = {"name": tool_name, "args": ""}
                        
                        # Send StartToolCall (b:)
                        yield f"b:{json.dumps({'toolCallId': tool_call_id, 'toolName': tool_name})}\n"
                        
                        # # Send ToolCall (9:) with complete args
                        # yield f"9:{json.dumps({'toolCallId': tool_call_id, 'toolName': tool_name, 'args': tool_args})}\n"
                
                # Handle streaming tool call chunks
                if hasattr(msg, 'tool_call_chunks') and msg.tool_call_chunks:
                    for chunk in msg.tool_call_chunks:
                        tool_name = chunk.get("name", "")
                        args_chunk = chunk.get("args", "")
                        chunk_index = chunk.get("index", 0)
                        tool_call_id = tool_calls_by_idx.get(chunk_index, -1)

                        # Accumulate args and send ToolCallArgsTextDelta (c:)
                        if tool_call_id != -1 and args_chunk:
                            tool_calls[tool_call_id]["args"] += args_chunk
                            yield f"c:{json.dumps({'toolCallId': tool_call_id, 'argsTextDelta': args_chunk})}\n"
                        

        # Send FinishMessage (d:) with usage stats
        yield f"d:{json.dumps({'finishReason': 'stop', 'usage': {'promptTokens': token_count, 'completionTokens': token_count}})}\n"
        
    except Exception as e:
        # Send Error (3:)
        error_message = str(e)
        yield f"3:{json.dumps(error_message)}\n"
