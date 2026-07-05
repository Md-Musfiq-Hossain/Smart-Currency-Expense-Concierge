# Smart Currency & Expense Concierge 🪙💼

An autonomous, secure, multi-agent financial gateway built with FastAPI and the Google Antigravity SDK. The system utilizes multimodal vision sub-agents to parse receipt images, converts non-USD transactions using an MCP exchange-rate tool, and enforces strict schema validation and indirect prompt injection guardrails (Day 4 Protocol) before database storage.

---

## 🚀 Key Features

* **Multi-Agent Orchestration**: A central `Orchestrator` agent manages the entire execution loop, delegating image parsing tasks to the specialized `VisionAgent` sub-agent.
* **Real-time Currency Conversion**: Seamlessly integrates with a standard Model Context Protocol (MCP) Exchange Rates server to retrieve live rates and convert transactions automatically.
* **Day 4 Security Guardrails**:
  * **Indirect Prompt Injection Protection**: Recursively filters parsed textual values using strict regex patterns to stop malicious commands embedded inside images (e.g., instructions-override strings, command executions) from executing.
  * **Strict Schema Enforcement**: Ensures the parsed expense records conform perfectly to expected data types and structural formats before committing them.
* **Robust Test Coverage**: Built-in end-to-end integration and security mock tests verify both processing and security containment flows.

---

## 📐 Architecture & Flow

For a detailed view of the sequence flow, see the [ARCHITECTURE.md](file:///D:/personal-project/vibecode_capstone_project/ARCHITECTURE.md) file.

```
Client  ──(Upload Image)──►  FastAPI App (app.py)  ──(Start Agent)──►  Orchestrator Agent
                                                                               │
       ┌───────────────────◄─── (Exchange Rates) ───► MCP Server               │ (Sub-agent Call)
       │                                                                       ▼
  Hooks Interceptor ◄─── (Propose Tool Execution) ─── save_to_database() ◄── VisionAgent
       │
       ├──► [Fail] Alert User & Block Execution
       └──► [Pass] Write to local database (financial_logs.json)
```

---

## 📁 Repository Structure

* [app.py]: The main FastAPI server host, containing endpoint routes, coordinator agent loops, and MCP configurations.
* [vision_agent.py]: Holds the [SubagentConfig] and JSON schema layout for the multimodal `VisionAgent` parsing sub-agent.
* [security.py]: Implements the Security hooks (`strict_validate_schema`, `check_for_injections`) mapped to the pre-tool-call `@decide` decorator.
* [database.py]: Exposes database helper tools (`save_to_database`, `get_database_logs`) to interact with the JSON datastore.
* [test_run.py]: Unit and integration tests validating security containment, schema enforcement, and end-to-end API orchestration.
* [mcp_config.json]: Configuration settings for the local exchange-rate MCP server launch.
* [AGENTS.md]: Policy definition document detailing multi-agent constraints and Day 4 safety guardrails.
* [ARCHITECTURE.md]: Visual flow diagrams and detailed component walkthroughs.

---

## ⚙️ Setup & Installation

### Prerequisites
1. **Python 3.10+**
2. **Node.js** (for running the Exchange Rates MCP Server via `npx`)

### 1. Install Dependencies
Ensure you have the required packages installed in your Python environment:
```bash
pip install fastapi uvicorn pydantic httpx
```
*Note: Make sure your environment has the `google-antigravity` SDK installed.*

### 2. Configure Credentials
Export your Gemini API Key:
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# Linux/macOS
export GEMINI_API_KEY="your-gemini-api-key-here"
```

### 3. Run the Server
Launch the FastAPI development server:
```bash
python app.py
```
The server will start running locally at `http://127.0.0.1:8000`.

---

## 📡 API Endpoints

### 1. Process Receipt
* **Endpoint**: `POST /upload-receipt`
* **Content-Type**: `multipart/form-data`
* **Arguments**:
  * `file`: (Required) The receipt image file (`receipt.jpg`, `receipt.png`, etc.)
  * `api_key`: (Optional) Overriding Gemini API key
* **Example Request (using curl)**:
  ```bash
  curl -X POST -F "file=@receipt.jpg" http://127.0.0.1:8000/upload-receipt
  ```
* **Sample Response (Success)**:
  ```json
  {
    "status": "success",
    "message": "Orchestrator loop completed.",
    "agent_summary": "Successfully parsed receipt. VisionAgent extracted: 2 items in EUR. Converted to USD using exchange rates. Saved to database.",
    "database_logs": {
      "items": [
        { "name": "Lunch Buffet", "original_cost": 15.00, "currency": "EUR", "usd_cost": 16.50 },
        { "name": "Soft Drink", "original_cost": 3.00, "currency": "EUR", "usd_cost": 3.30 }
      ],
      "date": "2026-07-05",
      "original_currency": "EUR"
    }
  }
  ```

### 2. View Database Logs
* **Endpoint**: `GET /logs`
* **Description**: Returns all financial logs recorded in [financial_logs.json].
* **Example Request**:
  ```bash
  curl http://127.0.0.1:8000/logs
  ```

---

## 🧪 Running Tests

Execute the suite of automated tests to verify schema validation and injection-containment:
```bash
python test_run.py
```
This runs the 5 target test cases:
1. `test_01_security_hook_safe_data`: Assures clean receipts with valid formatting pass through successfully.
2. `test_02_security_hook_prompt_injection`: Verifies injection strings are successfully intercepted and blocked.
3. `test_03_security_hook_invalid_schema`: Validates that corrupt formatting or wrong data types trigger immediate execution halt.
4. `test_04_end_to_end_orchestration_success`: Simulates a mock client receipt upload workflow.
5. `test_05_end_to_end_orchestration_injection_blocked`: Confirms malicious injections block the mock FastAPI processing loop.
