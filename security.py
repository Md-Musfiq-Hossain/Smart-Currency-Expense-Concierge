import re
from typing import Dict, Any, Union
from google.antigravity.hooks import pre_tool_call_decide, post_tool_call, HookContext
from google.antigravity.types import HookResult
from google.antigravity.types import ToolCall, ToolResult

# Day 4 security protocol: strict injection keywords to guard against indirect prompt injection
INJECTION_KEYWORDS = [
    r"ignore\s+all\s+previous",
    r"ignore\s+(all\s+)?instructions",
    r"system\s+instruction",
    r"override\s+instructions",
    r"run_command",
    r"delete\s+file",
    r"edit_file",
    r"eval\(",
    r"subprocess",
    r"system\(",
    r"\bsudo\b",
    r"__import__",
]

class SecurityException(Exception):
    """Exception raised when security validation fails."""
    pass

def strict_validate_schema(data: Dict[str, Any]) -> None:
    """
    Enforces strict schema validation for the receipt data.
    If the data is corrupt, has invalid types, or contains unexpected keys, raises ValueError.
    """
    if not isinstance(data, dict):
        raise ValueError("Financial log data must be a dictionary.")
    
    # Required top level fields
    if "items" not in data or "date" not in data:
        raise ValueError("Schema Error: Missing required fields ('items', 'date').")
        
    if not isinstance(data["items"], list):
        raise ValueError("Schema Error: 'items' field must be a list.")
        
    if not isinstance(data["date"], str) or not data["date"].strip():
        raise ValueError("Schema Error: 'date' field must be a non-empty string.")

    for idx, item in enumerate(data["items"]):
        if not isinstance(item, dict):
            raise ValueError(f"Schema Error: Item at index {idx} is not a dictionary.")
            
        required_item_keys = {"name", "original_cost", "currency"}
        # Ensure all required keys are present and have valid types
        if not required_item_keys.issubset(item.keys()):
            raise ValueError(f"Schema Error: Item at index {idx} is missing required fields {required_item_keys - item.keys()}.")
            
        if not isinstance(item["name"], str) or not item["name"].strip():
            raise ValueError(f"Schema Error: Item at index {idx} 'name' must be a non-empty string.")
            
        if not isinstance(item["original_cost"], (int, float)):
            raise ValueError(f"Schema Error: Item at index {idx} 'original_cost' must be a number.")
            
        if not isinstance(item["currency"], str) or len(item["currency"]) != 3:
            raise ValueError(f"Schema Error: Item at index {idx} 'currency' must be a 3-letter currency code.")

def check_for_injections(val: Any) -> None:
    """Recursively checks string values for known prompt injection patterns."""
    if isinstance(val, str):
        for pattern in INJECTION_KEYWORDS:
            if re.search(pattern, val, re.IGNORECASE):
                raise SecurityException(
                    f"Security Alert: Malicious prompt injection attempt detected in raw data: '{val}' matching pattern '{pattern}'."
                )
    elif isinstance(val, dict):
        for k, v in val.items():
            check_for_injections(k)
            check_for_injections(v)
    elif isinstance(val, list):
        for item in val:
            check_for_injections(item)

# Custom hook decorators mapped to google.antigravity.hooks

def decide(func):
    """
    Decorator to wrap a function as a PreToolCallDecideHook.
    The decorated function receives a ToolCall and returns a HookResult.
    """
    # Wrap with the SDK's native pre_tool_call_decide
    return pre_tool_call_decide(func)

def inspect(func):
    """
    Decorator to wrap a function as a PostToolCallHook.
    The decorated function receives a ToolResult and returns None.
    """
    # Wrap with the SDK's native post_tool_call
    return post_tool_call(func)

# Implement the Day 4 Security Hook using the @decide decorator

@decide
async def day4_security_guardrail(tool_call: ToolCall) -> HookResult:
    """
    Blocks tool calls (specifically save_to_database) if prompt injection is detected
    or if the financial logs violate strict schema enforcement.
    """
    if tool_call.name == "save_to_database":
        # Extract the parsed_data argument
        parsed_data = tool_call.args.get("parsed_data")
        if not parsed_data:
            return HookResult(allow=False, message="Security Error: No 'parsed_data' argument provided for save_to_database.")
            
        try:
            # 1. Strict Schema Enforcement
            strict_validate_schema(parsed_data)
            
            # 2. Indirect Injection Protection (Data Isolation)
            # Treat all text strictly as raw data and reject any containing system injections.
            check_for_injections(parsed_data)
            
        except (ValueError, SecurityException) as e:
            # Halt execution and alert the user by returning a denied HookResult
            return HookResult(allow=False, message=str(e))
            
    return HookResult(allow=True)
