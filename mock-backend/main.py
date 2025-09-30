"""Main FastAPI server with LangGraph integration."""
import sys
import os
sys.dont_write_bytecode = True

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from typing import Annotated
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends

# Utils and modules
from lib.auth import get_authenticated_user

# Run orchestration
from orchestration import get_orchestrator
orchestrator = get_orchestrator()
orchestrator.start()

# Initialize FastAPI app
app = FastAPI(title="LangGraph Azure Inference API", version="1.0.0")

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root(username: Annotated[str, Depends(get_authenticated_user)]):
    """Root endpoint."""
    return {"message": "LangGraph Azure Inference API is running", "authenticated_user": username}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Add external routers
from routes.chat_conversation import chat_conversation_route
from routes.file_indexing import file_indexing_route

app.include_router(
    chat_conversation_route
)

app.include_router(
    file_indexing_route,
    prefix="/api/v1",
    tags=["file-indexing"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
