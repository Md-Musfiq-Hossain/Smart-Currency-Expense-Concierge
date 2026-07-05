import os
import json
from typing import Dict, Any, List

DATABASE_FILE = os.path.join(os.path.dirname(__file__), "financial_logs.json")

def save_to_database(parsed_data: Dict[str, Any]) -> str:
    """
    Saves the parsed and converted expense data to the local database file.
    
    Args:
        parsed_data: A dictionary containing:
            - items: List of dicts, each with keys 'name', 'original_cost', 'currency', and 'usd_cost'.
            - date: Date of the receipt.
            - original_currency: The currency of the original receipt.
            
    Returns:
        A confirmation message.
    """
    # Load existing logs
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    else:
        logs = []
        
    logs.append(parsed_data)
    
    # Save back
    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
        
    return f"Successfully saved receipt with {len(parsed_data.get('items', []))} items to local database."

def get_database_logs() -> List[Dict[str, Any]]:
    """Retrieves all financial logs from the local database."""
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []
