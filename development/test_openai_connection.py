"""
Test script to verify OpenAI Assistants API connection.
"""

import os
from dotenv import load_dotenv
from core.openai_assistant import get_openai_client, build_run_package

# Load environment variables
load_dotenv()

def test_connection():
    """Test OpenAI connection and Assistant access."""
    print("="*60)
    print("Testing OpenAI Assistants API Connection")
    print("="*60)
    print()
    
    # Check environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    
    print("1. Checking Environment Variables:")
    print(f"   API Key: {'[OK] Set' if api_key else '[FAIL] Missing'}")
    if api_key:
        print(f"      (starts with: {api_key[:20]}...)")
    print(f"   Assistant ID: {'[OK] Set' if assistant_id else '[FAIL] Missing'}")
    if assistant_id:
        print(f"      ({assistant_id})")
    print()
    
    if not api_key or not assistant_id:
        print("[FAIL] Missing required environment variables!")
        print("   Please check your .env file.")
        return False
    
    # Test client initialization
    print("2. Testing Client Initialization:")
    try:
        client = get_openai_client()
        if client:
            print("   [OK] OpenAI client initialized successfully")
        else:
            print("   [FAIL] Failed to initialize OpenAI client")
            return False
    except Exception as e:
        print(f"   [FAIL] Error: {e}")
        return False
    print()
    
    # Test Assistant retrieval
    print("3. Testing Assistant Access:")
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        print(f"   [OK] Assistant found: {assistant.name if hasattr(assistant, 'name') else 'Unnamed'}")
        print(f"      Model: {assistant.model if hasattr(assistant, 'model') else 'Unknown'}")
    except Exception as e:
        print(f"   [FAIL] Error retrieving Assistant: {e}")
        return False
    print()
    
    # Test run package assembly
    print("4. Testing Run Package Assembly:")
    try:
        test_spec = {
            "newsletter_name": "Test Newsletter",
            "categories": ["company_news", "regional_monitoring"],
            "regions": ["EMEA"],
            "frequency": "weekly"
        }
        run_package = build_run_package(
            specification=test_spec,
            cadence="weekly"
        )
        print("   [OK] Run package assembled successfully")
        print(f"      System instruction length: {len(run_package['system_instruction'])} chars")
        print(f"      User message length: {len(run_package['user_message'])} chars")
    except Exception as e:
        print(f"   [FAIL] Error assembling run package: {e}")
        return False
    print()
    
    print("="*60)
    print("[OK] All tests passed! OpenAI integration is ready.")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Run the Generator app: streamlit run generator_app.py")
    print("  2. Create a specification in the Configurator")
    print("  3. Generate a newsletter in the Generator")
    
    return True

if __name__ == "__main__":
    test_connection()

