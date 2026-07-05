import os
import shutil
import tempfile
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Antigravity imports
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig, from_file
from google.antigravity.types import McpStdioServer
from google.antigravity.hooks import policy

# Project imports
from database import save_to_database, get_database_logs
from vision_agent import VISION_AGENT_CONFIG
from security import day4_security_guardrail

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ExpenseConcierge")

app = FastAPI(
    title="Smart Currency & Expense Concierge",
    description="Multi-agent FastAPI system for multimodal receipt parsing and currency conversion",
    version="1.0.0"
)

COORDINATOR_SYSTEM_INSTRUCTIONS = """
You are the OrchestratorAgent for the "Smart Currency & Expense Concierge" project.
Your goal is to coordinate receipt parsing, currency conversion, and database saving.

You have access to:
1. `VisionAgent` sub-agent: Use the `start_subagent` tool. Pass it the receipt image and ask it to parse the items and date.
2. `currency-converter` MCP server tools: Exposes exchange rate/conversion capabilities (e.g. `mcp_currency-converter_convert_currency` or similar).
3. `save_to_database` custom tool: Saves the processed expense items to the database.

Strictly adhere to the following protocol:
1. Call the `VisionAgent` sub-agent with the receipt image content to extract the raw items (name, original_cost, currency) and date.
2. For each extracted item:
   - If the currency is NOT USD, call the currency-converter tool to obtain the rate and convert it to USD.
   - If the currency is USD, the usd_cost is equal to the original_cost.
3. Formulate the final payload containing the list of items (each with name, original_cost, currency, and usd_cost) and the date.
4. Pass this payload to the `save_to_database` tool.
5. Provide a clear summary of the saved items and conversion rates used to the user.
"""

# Define the currency-converter MCP configuration
mcp_server = McpStdioServer(
    name="currency-converter",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-exchange-rates"],
    env={}
)

def get_agent_config(api_key: str = None) -> LocalAgentConfig:
    """Helper to construct the agent configuration."""
    return LocalAgentConfig(
        system_instructions=COORDINATOR_SYSTEM_INSTRUCTIONS,
        tools=[save_to_database],
        policies=[policy.allow_all()], # Essential safety policy to run MCP/write tools
        hooks=[day4_security_guardrail], # Day 4 hook validation before saving
        mcp_servers=[mcp_server],
        subagents=[VISION_AGENT_CONFIG],
        api_key=api_key or os.getenv("GEMINI_API_KEY", "dummy-api-key"),
        workspaces=[os.path.dirname(os.path.abspath(__file__))]
    )

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Smart Currency & Expense Concierge",
        "description": "Multi-agent orchestration system for receipt processing and real-time USD conversion"
    }

@app.get("/logs", response_model=List[Dict[str, Any]])
def get_logs():
    """Retrieves all financial logs from the local database."""
    try:
        return get_database_logs()
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-receipt")
async def upload_receipt(
    file: UploadFile = File(...),
    api_key: str = None
):
    """
    Endpoint to upload a receipt image, trigger the orchestrator agent loop
    to parse and convert currencies to USD, and save it to the database.
    """
    logger.info(f"Received receipt upload request for file: {file.filename}")
    
    # Check file type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files (JPEG, PNG, etc.) are supported.")

    # Save uploaded file to a temporary file
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    try:
        # Load receipt media using from_file()
        receipt_media = from_file(temp_path, description="Receipt image for parsing")
        
        # Instantiate agent configuration
        config = get_agent_config(api_key)
        
        logger.info("Initializing Antigravity orchestrator agent session...")
        async with Agent(config) as agent:
            # Construct the prompt payload
            prompt = [
                "Orchestrate receipt parsing, conversion, and saving for this receipt image.",
                receipt_media
            ]
            
            # Run the agent chat loop
            logger.info("Sending prompt to orchestrator agent...")
            chat_response = await agent.chat(prompt)
            
            # Read full agent response text
            response_text = ""
            async for token in chat_response:
                response_text += token
                
            return JSONResponse(content={
                "status": "success",
                "message": "Orchestrator loop completed.",
                "agent_summary": response_text,
                "database_logs": get_database_logs()[-1] if get_database_logs() else {}
            })
            
    except Exception as e:
        logger.exception("An error occurred during receipt processing")
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")
        
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as ce:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {ce}")

if __name__ == "__main__":
    import uvicorn
    # Start FastAPI app on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
