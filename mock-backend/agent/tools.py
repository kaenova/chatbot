"""Tools for the LangGraph agent.

This module provides various tools that can be used by the LangGraph agent:

1. get_current_time: Get current date and time
2. SessionsPythonREPLTool: Execute Python code (requires AZURE_SESSIONPOOL_ENDPOINT)
3. web_search: Perform web search using SearxNG (requires SEARXNG_URL)
4. Azure AI Search tools (require AZURE_SEARCH_* environment variables):
   - azure_search_documents: Text-based search
   - azure_search_semantic: Semantic search with AI ranking
   - azure_search_filter: Search with OData filters
   - azure_search_vector: Vector similarity search (requires Azure OpenAI)

Environment Variables Required:
- AZURE_SEARCH_ENDPOINT: Your Azure AI Search service endpoint
- AZURE_SEARCH_KEY: Your Azure AI Search admin key
- AZURE_SEARCH_INDEX_NAME: The search index to query
- AZURE_SEARCH_SEMANTIC_CONFIG: Semantic configuration name (optional, defaults to 'default')
- AZURE_SEARCH_VECTOR_FIELD: Vector field name (optional, defaults to 'content_vector')
- AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint (for vector search)
- AZURE_OPENAI_KEY: Azure OpenAI key (for vector search)
- AZURE_OPENAI_EMBEDDING_MODEL: Embedding model name (optional, defaults to 'text-embedding-ada-002')
"""
import os
from datetime import datetime
from langchain_core.tools import tool
from langchain_azure_dynamic_sessions import SessionsPythonREPLTool
from langchain_community.utilities import SearxSearchWrapper
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
# Load environment variables from .env file if present
load_dotenv()


tool_generator = []

@tool
def get_current_time() -> str:
    """Get the current date and time.
    
    Returns:
        str: Current date and time in ISO format
    """
    return datetime.now().isoformat()
tool_generator.append(get_current_time)


if os.getenv("AZURE_SESSIONPOOL_ENDPOINT"):
    code_tool = SessionsPythonREPLTool(
        pool_management_endpoint=os.getenv("AZURE_SESSIONPOOL_ENDPOINT")
    )
    tool_generator.append(code_tool)

if os.getenv("SEARXNG_URL"):
    search = SearxSearchWrapper(searx_host=os.getenv("SEARXNG_URL"))

    @tool
    def web_search(query: str) -> str:
        """Perform a web search using SearxNG.
        
        Args:
            query: Search query string
            
        Returns:
            str: Search results
        """
        results = search.results(
            query,
            num_results=5,
        )

        if not results:
            return f"No results found for query: '{query}'"
        
        print(f"Web search results: {results}")
        
        final_results = "Search results:\n"
        for x in results:
            final_results += f"""
# {x["title"]} 
- URL: {x["link"]}
- Snippet: {x["snippet"]}\n"""

        return final_results

    tool_generator.append(web_search)

# Azure AI Search tools
if (os.getenv("AZURE_SEARCH_ENDPOINT") and 
    os.getenv("AZURE_SEARCH_API_KEY") and 
    os.getenv("AZURE_SEARCH_INDEX_NAME")):
    
    search_client = SearchClient(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY"))
    )

    @tool
    def azure_search_documents(query: str, top: int = 5) -> str:
        """Search documents in Azure AI Search using text-based search.
        
        Args:
            query: Search query string
            top: Number of results to return (default: 5, max: 50)
            
        Returns:
            str: Formatted search results with titles, content, and metadata
        """
        try:
            top = min(max(1, top), 50)  # Ensure top is between 1 and 50
            results = search_client.search(
                search_text=query,
                top=top,
                include_total_count=True
            )
            
            formatted_results = []
            for result in results:
                formatted_result = {
                    "score": getattr(result, "@search.score", "N/A"),
                    "title": result.get("title", "No title"),
                    "content": result.get("content", "No content"),
                    "metadata": {k: v for k, v in result.items() if not k.startswith("@") and k not in ["title", "content"]}
                }
                formatted_results.append(formatted_result)
            
            if not formatted_results:
                return f"No results found for query: '{query}'"
            
            # Format results as readable text
            output = f"Found {len(formatted_results)} results for '{query}':\n\n"
            for result in formatted_results:
                filename = result['metadata'].get('filename', 'Unknown')
                chunk_index = result['metadata'].get('chunk_index', 0)
                id_ = result['metadata'].get('id', 'Unknown')
                content = result['content']
                output += f"# File: {filename} Chunk [{chunk_index}]\n"
                output += f"**chunk_id/id**: `{id_}`\n"
                output += "Content:\n```\n"
                output += f"{content}\n"
                output += "```\n\n"
            
            return output
            
        except Exception as e:
            return f"Error searching Azure AI Search: {str(e)}"

    tool_generator.append(azure_search_documents)

    @tool
    def azure_search_semantic(query: str, top: int = 5) -> str:
        """Search documents in Azure AI Search using semantic search capabilities.
        
        Args:
            query: Search query string
            top: Number of results to return (default: 5, max: 50)
            
        Returns:
            str: Formatted semantic search results with relevance scores
        """
        try:
            top = min(max(1, top), 50)  # Ensure top is between 1 and 50
            
            # Check if semantic search is configured
            semantic_config = "my-semantic-config"
            
            results = search_client.search(
                search_text=query,
                top=top,
                query_type="semantic",
                semantic_configuration_name=semantic_config,
                query_caption="extractive",
                query_answer="extractive",
                include_total_count=True
            )
            
            formatted_results = []
            for result in results:
                # Get semantic captions if available
                captions = getattr(result, "@search.captions", [])
                caption_text = captions[0].text if captions else result.get("content", "No content")[:300]
                
                formatted_result = {
                    "score": getattr(result, "@search.score", "N/A"),
                    "title": result.get("title", "No title"),
                    "caption": caption_text,
                    "content": result.get("content", "No content"),
                    "metadata": {k: v for k, v in result.items() if not k.startswith("@") and k not in ["title", "content"]}
                }
                formatted_results.append(formatted_result)
            
            if not formatted_results:
                return f"No semantic results found for query: '{query}'"
            
            # Format results as readable text
            output = f"Found {len(formatted_results)} semantic results for '{query}':\n\n"
            for result in formatted_results:
                filename = result['metadata'].get('filename', 'Unknown')
                chunk_index = result['metadata'].get('chunk_index', 0)
                id_ = result['metadata'].get('id', 'Unknown')
                content = result['content']
                output += f"# File: {filename} Chunk [{chunk_index}]\n"
                output += f"**chunk_id/id**: `{id_}`\n"
                output += "Content:\n```\n"
                output += f"{content}\n"
                output += "```\n\n"
            
            return output
            
        except Exception as e:
            return f"Error performing semantic search: {str(e)}"

    tool_generator.append(azure_search_semantic)

    @tool
    def azure_search_filter(query: str, filter_expression: str, top: int = 5) -> str:
        """Search documents in Azure AI Search with OData filter expressions.
        
        Args:
            query: Search query string
            filter_expression: OData filter expression (e.g., "category eq 'technology'")
            top: Number of results to return (default: 5, max: 50)
            
        Returns:
            str: Formatted filtered search results
        """
        try:
            top = min(max(1, top), 50)  # Ensure top is between 1 and 50
            results = search_client.search(
                search_text=query,
                filter=filter_expression,
                top=top,
                include_total_count=True
            )
            
            formatted_results = []
            for result in results:
                formatted_result = {
                    "score": getattr(result, "@search.score", "N/A"),
                    "title": result.get("title", "No title"),
                    "content": result.get("content", "No content"),
                    "metadata": {k: v for k, v in result.items() if not k.startswith("@") and k not in ["title", "content"]}
                }
                formatted_results.append(formatted_result)
            
            if not formatted_results:
                return f"No results found for query: '{query}' with filter: '{filter_expression}'"
            
            # Format results as readable text
            output = f"Found {len(formatted_results)} filtered results for '{query}' (Filter: {filter_expression}):\n\n"
            for result in formatted_results:
                filename = result['metadata'].get('filename', 'Unknown')
                chunk_index = result['metadata'].get('chunk_index', 0)
                id_ = result['metadata'].get('id', 'Unknown')
                content = result['content']
                output += f"# File: {filename} Chunk [{chunk_index}]\n"
                output += f"**chunk_id/id**: `{id_}`\n"
                output += "Content:\n```\n"
                output += f"{content}\n"
                output += "```\n\n"
            
            return output
            
        except Exception as e:
            return f"Error performing filtered search: {str(e)}"

    tool_generator.append(azure_search_filter)

    # Vector search tool (requires vector embeddings)
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        try:
            from openai import AzureOpenAI
            
            openai_client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            
            @tool
            def azure_search_vector(query: str, top: int = 5) -> str:
                """Search documents in Azure AI Search using vector similarity.
                
                Args:
                    query: Search query string to convert to vector
                    top: Number of results to return (default: 5, max: 50)
                    
                Returns:
                    str: Formatted vector search results with similarity scores
                """
                try:
                    top = min(max(1, top), 50)  # Ensure top is between 1 and 50
                    
                    # Generate embedding for the query
                    embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-ada-002")
                    response = openai_client.embeddings.create(
                        input=query,
                        model=embedding_model
                    )
                    query_vector = response.data[0].embedding
                    
                    # Perform vector search
                    vector_field = "content_vector"
                    vector_query = VectorizedQuery(
                        vector=query_vector,
                        k_nearest_neighbors=top,
                        fields=vector_field
                    )
                    
                    results = search_client.search(
                        search_text=None,
                        vector_queries=[vector_query],
                        top=top
                    )
                    
                    formatted_results = []
                    for result in results:
                        formatted_result = {
                            "title": result.get("title", "No title"),
                            "content": result.get("content", "No content"),
                            "metadata": {k: v for k, v in result.items() if not k.startswith("@") and k not in ["title", "content", vector_field]}
                        }
                        formatted_results.append(formatted_result)
                    
                    if not formatted_results:
                        return f"No vector results found for query: '{query}'"
                    
                    # Format results as readable text
                    output = f"Found {len(formatted_results)} vector similarity results for '{query}':\n\n"
                    for result in formatted_results:
                        filename = result['metadata'].get('filename', 'Unknown')
                        chunk_index = result['metadata'].get('chunk_index', 0)
                        id_ = result['metadata'].get('id', 'Unknown')
                        content = result['content']
                        output += f"# File: {filename} Chunk [{chunk_index}]\n"
                        output += f"**chunk_id/id**: {id_}\n"
                        output += "Content:\n```\n"
                        output += f"{content}\n"
                        output += "```\n\n"
                    
                    return output
                    
                except Exception as e:
                    return f"Error performing vector search: {str(e)}"

            tool_generator.append(azure_search_vector)
            
        except ImportError:
            pass  # OpenAI client not available


print(f"✓ Tools loaded. Tools available: {[tool.name for tool in tool_generator]}")
# List of available tools
AVAILABLE_TOOLS = tool_generator