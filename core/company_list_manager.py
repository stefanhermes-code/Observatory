"""
Company List Manager for PU Observatory.
Handles uploading and managing company lists in OpenAI Assistant's vector store.
"""

import os
import json
from typing import Optional, Dict, List
from pathlib import Path

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def get_openai_client() -> Optional[object]:
    """Initialize and return OpenAI client."""
    if not OPENAI_AVAILABLE:
        return None
    
    # Try Streamlit secrets first (for Streamlit Cloud), then environment variables (for local .env)
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except (AttributeError, FileNotFoundError, RuntimeError):
        # Not running in Streamlit or secrets not available, use environment variables
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def load_company_list(file_path: Optional[str] = None) -> Dict:
    """
    Load company list from JSON file.
    
    Args:
        file_path: Path to company list JSON file. Defaults to development/company_list.json
    
    Returns:
        Dictionary containing company list data
    """
    if file_path is None:
        file_path = Path(__file__).parent.parent / "development" / "company_list.json"
    else:
        file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Company list file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_company_list_for_assistant(company_data: Dict) -> str:
    """
    Format company list data into a readable text format for the Assistant.
    
    Args:
        company_data: Company list dictionary
    
    Returns:
        Formatted text string
    """
    lines = [
        "# PU Industry Company List",
        "",
        f"Last Updated: {company_data.get('last_updated', 'Unknown')}",
        "",
        "## Companies to Track:",
        ""
    ]
    
    for company in company_data.get("companies", []):
        if company.get("status") != "active":
            continue  # Skip inactive companies
        
        lines.append(f"### {company['name']}")
        
        if company.get("aliases"):
            aliases = ", ".join(company["aliases"])
            lines.append(f"**Also known as:** {aliases}")
        
        if company.get("value_chain_position"):
            positions = ", ".join(company["value_chain_position"])
            lines.append(f"**Value Chain Position:** {positions}")
        
        if company.get("regions"):
            regions = ", ".join(company["regions"])
            lines.append(f"**Regions:** {regions}")
        
        if company.get("notes"):
            lines.append(f"**Notes:** {company['notes']}")
        
        lines.append("")
    
    lines.extend([
        "## Company Categories:",
        ""
    ])
    
    categories = company_data.get("categories", {})
    for category, companies in categories.items():
        lines.append(f"**{category}:** {', '.join(companies)}")
        lines.append("")
    
    return "\n".join(lines)


def upload_company_list_to_assistant(
    assistant_id: Optional[str] = None,
    company_list_path: Optional[str] = None
) -> Dict:
    """
    Upload company list file to OpenAI and attach it to the Assistant's vector store.
    
    Args:
        assistant_id: OpenAI Assistant ID. If None, reads from OPENAI_ASSISTANT_ID env var
        company_list_path: Path to company list JSON file
    
    Returns:
        Dictionary with file_id and vector_store_id
    """
    client = get_openai_client()
    if not client:
        raise Exception("OpenAI client not available. Check OPENAI_API_KEY.")
    
    if assistant_id is None:
        # Try Streamlit secrets first (for Streamlit Cloud), then environment variables (for local .env)
        try:
            import streamlit as st
            assistant_id = st.secrets.get("OPENAI_ASSISTANT_ID") or os.getenv("OPENAI_ASSISTANT_ID")
        except (AttributeError, FileNotFoundError, RuntimeError):
            # Not running in Streamlit or secrets not available, use environment variables
            assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
        if not assistant_id:
            raise Exception("Assistant ID not provided and OPENAI_ASSISTANT_ID not set in Streamlit Cloud secrets or .env file.")
    
    # Load and format company list
    company_data = load_company_list(company_list_path)
    formatted_text = format_company_list_for_assistant(company_data)
    
    # Create a properly named text file for upload (instead of temp file)
    import tempfile
    import os
    # Use a descriptive filename instead of random temp name
    upload_dir = tempfile.gettempdir()
    tmp_file_path = os.path.join(upload_dir, "pu_company_list.txt")
    
    # Write formatted text to file
    with open(tmp_file_path, 'w', encoding='utf-8') as tmp_file:
        tmp_file.write(formatted_text)
    
    try:
        # Step 1: Upload file to OpenAI
        with open(tmp_file_path, 'rb') as file:
            uploaded_file = client.files.create(
                file=file,
                purpose="assistants"
            )
        file_id = uploaded_file.id
        
        # Step 2: Get or create vector store for the Assistant
        # First, check if vector store ID is in .env
        # Try Streamlit secrets first (for Streamlit Cloud), then environment variables (for local .env)
        try:
            import streamlit as st
            vector_store_id = st.secrets.get("OPENAI_VECTOR_STORE_ID") or os.getenv("OPENAI_VECTOR_STORE_ID")
        except (AttributeError, FileNotFoundError, RuntimeError):
            # Not running in Streamlit or secrets not available, use environment variables
            vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
        
        if vector_store_id:
            print(f"[INFO] Using vector store from .env: {vector_store_id}")
        else:
            # If not in .env, check if Assistant already has a vector store
            assistant = client.beta.assistants.retrieve(assistant_id)
            
            if hasattr(assistant, 'tool_resources') and assistant.tool_resources:
                if hasattr(assistant.tool_resources, 'file_search') and assistant.tool_resources.file_search:
                    if hasattr(assistant.tool_resources.file_search, 'vector_store_ids'):
                        vector_store_ids = assistant.tool_resources.file_search.vector_store_ids
                        if vector_store_ids:
                            vector_store_id = vector_store_ids[0]
                            print(f"[INFO] Found existing vector store on Assistant: {vector_store_id}")
            
            # If still no vector store exists, create one
            if not vector_store_id:
                vector_store = client.beta.vector_stores.create(
                    name="PU Industry Company List"
                )
                vector_store_id = vector_store.id
                print(f"[INFO] Created new vector store: {vector_store_id}")
                print(f"[INFO] Add this to your .env file: OPENAI_VECTOR_STORE_ID={vector_store_id}")
        
        # Step 3: Add file to vector store
        client.beta.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
        
        # Step 4: Update Assistant to use the vector store and enable file_search tool
        # First, check current tools
        current_tools = assistant.tools if hasattr(assistant, 'tools') else []
        tool_names = [tool.type if isinstance(tool, dict) else getattr(tool, 'type', None) for tool in current_tools]
        
        # Ensure file_search tool is enabled
        if 'file_search' not in tool_names:
            current_tools.append({"type": "file_search"})
        
        # Update Assistant with vector store and tools
        client.beta.assistants.update(
            assistant_id=assistant_id,
            tools=current_tools,
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
        )
        
        return {
            "file_id": file_id,
            "vector_store_id": vector_store_id,
            "status": "success"
        }
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_file_path)
        except:
            pass


def update_company_list_file(
    company_list_path: Optional[str] = None,
    companies: Optional[List[Dict]] = None
) -> None:
    """
    Update the company list JSON file.
    
    Args:
        company_list_path: Path to company list JSON file
        companies: List of company dictionaries to update
    """
    if company_list_path is None:
        company_list_path = Path(__file__).parent.parent / "development" / "company_list.json"
    else:
        company_list_path = Path(company_list_path)
    
    if companies is None:
        raise ValueError("Companies list is required")
    
    from datetime import datetime
    
    # Load existing data or create new
    if company_list_path.exists():
        with open(company_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {
            "version": "1.0",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "companies": [],
            "categories": {}
        }
    
    # Update companies
    data["companies"] = companies
    data["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Rebuild categories
    categories = {}
    for company in companies:
        if company.get("status") != "active":
            continue
        for position in company.get("value_chain_position", []):
            if position not in categories:
                categories[position] = []
            if company["name"] not in categories[position]:
                categories[position].append(company["name"])
    
    data["categories"] = categories
    
    # Save updated file
    with open(company_list_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

