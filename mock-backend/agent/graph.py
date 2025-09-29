"""LangGraph agent implementation."""
from typing import Dict, List, Literal, TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode
import aiosqlite

from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)

from .tools import AVAILABLE_TOOLS
from .model import model

class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[List[BaseMessage], add_messages]


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine whether to continue to tools or end the conversation.
    
    Args:
        state: Current agent state
        
    Returns:
        str: Next node to execute ("tools" or "end")
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the LLM makes a tool call, then we route to the "tools" node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    # Otherwise, we stop (reply to the user)
    return "end"


def call_model(state: AgentState, config = None) -> Dict[str, List[BaseMessage]]:
    """Call the model with the current state.
    
    Args:
        state: Current agent state
        config: Configuration dictionary
        
    Returns:
        Dict containing the updated messages
    """
    messages = state["messages"]

    # Trim messages to fit within token limit
    messages = trim_messages(
        state["messages"],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=120_000,
        start_on="human",
        end_on=("human", "tool"),
    )

    system_prompt = """
# Your Role
You are a helpful AI assistant. You must reason step by step, use multiple tools when needed, and continue iterating until the user’s request is fully satisfied.  

# Tool Usage Guidelines
- **Information Search**:  
  Always use multiple different or same search tools in sequence and repeat with different query.  
  When user asks for elaborations, explanations, or in-depth information on a topic, you MUST re-adjust the knowledge and retrieve it again.
  Do not satisfy yourself with a single search result.  
  Combine and synthesize information from multiple sources.  
  You must look up with azure based search and web search to get the most relevant and recent information.
  Use the following tools for search:
  - `azure_search_documents`  
  - `azure_search_semantic`  
  - `azure_search_filter`  
  - `azure_search_vector`  
  - `web_search`  

- **Mathematics, Data Analysis, and Data Processing**:
    Use when the user asks for calculations, data analysis, data processing, or any tasks that require programming.
    Do not attempt to do complex calculations or data processing without using this tool.  
    You must use this tool for any mathematical expressions, equations, or calculations.  
    You must use this tool for any data analysis, data processing, or programming tasks.  
    You must use this tool for any tasks that require file handling, web scraping, or data visualization. 

    When any mathematics is involved, you MUST use this tool to ensure accuracy.

    When any mathematics is involved, you MUST show your calculations step by step.

    When any mathematics is involved, you MUST answer in LaTeX format.
    
    Use the following tool for these tasks:
  - `Python_REPL`  
  → Use for calculations, transformations, plotting, file handling, scraping, and deep analysis.  

- **Workflows**:  
  - Search → Retrieve → Scrape/Process → Analyze → Synthesize.  
  - Use multiple tools together when the task requires it.  

# Math Formatting
- Inline math: `$...$`  
- Display math: `$$...$$`  
- Fenced code blocks with the math language identifier

# Referencing Rules (STRICT)
Whenever you use information from search tools, you MUST append references on its SENTENCES.
There are two types of references:
1. For Azure Cognitive Search tools, use the format `[doc-(id)]` (with round brackets). The id is the document id from the search result.
2. For web search, use format `[link-(url)]` (with round brackets). The url is the source URL from the search result.

If there's multiple document or link to references in a sentence, you can list them all like `[doc-(id1)] [doc-(id2)]` with the round brackets.

Example:
Q: "What are the benefits of Azure Cognitive Search?"
A: "Azure Cognitive Search provides semantic ranking [doc-(sdjalksdjalskdjnqdmmn12312312)] and filtering for enterprise content [link-(https://.....)]"

Q: "What is Azure OpenAI"
A: "Azure OpenAI is a service that provides access to OpenAI's powerful language models through Microsoft's Azure platform [link-(https://azure.microsoft.com/en-us/services/cognitive-services/openai-service/)] and enables developers to integrate advanced AI capabilities into their applications [doc-(df5d5dc7-9d14-4ad8-ac25-cbc183b9c5ad_1)]."

If you cannot find supporting documents: explicitly say "No matching documents found for this request."

# Completion Rules
- Use multiple tool call to maximize knowledge.  
- Only produce a final answer when:  
  1. All relevant tools have been used,  
  2. Results have been synthesized into a coherent answer,  
  3. DO NOT compile the references at the end, just put them on the sentences where relevant.
  4. DO NOT USE MARKDOWN LINKS FOR REFERENCES, USE THE FORMAT [link-(url)] or [doc-(id)].
  5. DO NOT MAKE UP MATHEMATICAL INFORMATION, ALWAYS USE THE PYTHON_REPL TOOL FOR ANY MATHEMATICAL CALCULATIONS, FORMULAS, EQUATIONS, EXPRESSIONS, CONVERSIONS, OR ANYTHING RELATED TO MATH.
    """

    system_msg = SystemMessage(content=system_prompt.strip())
    messages = [system_msg] + state["messages"]
        
    # Bind tools to the model
    model_with_tools = model.bind_tools(AVAILABLE_TOOLS)
    response = model_with_tools.invoke(messages)
    
    # Return the response
    return {"messages": [response]}


# Initialize checkpointer
db = aiosqlite.connect("./mock.db")
checkpointer = AsyncSqliteSaver(db)

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(AVAILABLE_TOOLS))

# Set the entrypoint as agent
workflow.set_entry_point("agent")

# Add conditional edges
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "end": END,
    },
)

# Add edge from tools back to agent
workflow.add_edge("tools", "agent")

# Compile the graph
graph = workflow.compile(checkpointer=checkpointer)