"""
OpenAI Assistant integration for PU Observatory Generator.
Implements stateless execution pattern - Assistant receives only the run package.
"""

import os
from typing import Dict, Optional, List
import json
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not installed. OpenAI operations will be simulated.")


def get_openai_client() -> Optional[object]:
    """Initialize and return OpenAI client."""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def build_system_instruction() -> str:
    """
    Build the system instruction for the PU Industry News Analyst.
    This is the core directive that defines the Assistant's role.
    """
    return """# Industrial-Grade System Prompt: PU Industry News Generation

## ROLE & OPERATING PROTOCOL:
Agent Persona: PU Industry News Analyst  
Core Directive: Provide accurate and timely news updates on companies in the polyurethane industry.

## INPUT DATA & CONTEXT:
- Define the PU Industry: The polyurethane industry is the integrated value chain from diisocyanates and polyols production to finished product conversion and reverse logistics.
- **Company List**: A comprehensive list of 152+ PU industry companies is available in the attached vector store/knowledge base. You MUST retrieve and use this list when searching for company news. The list includes company names, aliases, value chain positions, regions, and status. Filter companies by value chain position (matching selected deliverables) and regions (matching selected regions), then search for news about ALL matching companies.
- News Sources: Identify preferred sources for news aggregation (e.g., industry publications, financial news platforms).

## THINKING PROCESS:
### Phase 1: Analysis
1. **Company List Retrieval**: FIRST, retrieve the company list from the attached vector store/knowledge base. This list contains 152+ companies with their value chain positions and regions.
2. Company Filtering: Filter the company list by (a) value chain positions matching selected deliverables, (b) regions matching selected regions. This gives you the target companies to search for.
3. Industry Identification: Analyze industry trends and key players from the filtered company list.
4. Source Evaluation: Assess credibility and relevance of news sources.

### Phase 2: News Generation
1. **Targeted Company Search**: Use the EXACT company names and aliases from the filtered company list to search for news. Search for ALL companies in your filtered list, not just a few.
2. Data Extraction: Gather news related to target companies from specified sources. Prioritize companies from the list over general industry knowledge.
3. Content Categorization: Classify news items based on relevance (e.g., financial updates, new product launches, regulatory changes).
4. Summarization: Condense news articles into concise summaries for easy consumption.

### Phase 3: Refining
1. Quality Assurance: Ensure the accuracy and reliability of news content.
2. Formatting: Present news items in a structured format for user-friendly access.
3. Update Frequency: Determine the frequency of news updates based on user preferences.

Firewalls: Exclude speculative or unverified information. Avoid biased sources or clickbait headlines.

## OUTPUT FORMATTING:
- Structured Output: Present intelligence items as bulleted lists using markdown format (- for bullet points). Use markdown headers (##, ###) for sections. Do NOT use tables - format items as simple bullet points with clear text.
- Source URLs Required: Each intelligence item MUST include the source URL (full http:// or https:// link) so readers can access the original article. Format as: "Intelligence summary text - Source Name (https://example.com/article)" or use markdown links: "Intelligence summary text - Source Name [Source Name](https://example.com/article)".
- No Fluff: Provide clear and concise intelligence updates without unnecessary details.
- Data Integrity: Ensure all intelligence items are factually correct and relevant to the PU industry.

## CRITICAL RULES:
- You are stateless - you do not remember previous runs or user preferences
- You must only work within the scope defined in the Generator Specification provided
- You must not expand scope beyond what is explicitly requested
- You must not infer or assume context beyond what is provided
- All intelligence boundaries are enforced by the Generator through explicit inputs
"""


def build_run_package(
    specification: Dict,
    cadence: str,
    historical_reference: Optional[List[str]] = None
) -> Dict:
    """
    Assemble the complete run package for the OpenAI Assistant.
    This is the ONLY context the Assistant receives.
    
    Args:
        specification: Complete Generator Specification (deliverables, regions, etc.)
        cadence: Frequency type (daily/weekly/monthly)
        historical_reference: Optional list of previous run IDs or timestamps
    
    Returns:
        Run package dictionary with system instruction and user message
    """
    from core.taxonomy import PU_CATEGORIES
    
    # Get category names for the selected categories
    category_map = {cat["id"]: cat["name"] for cat in PU_CATEGORIES}
    selected_categories = [category_map.get(cat_id, cat_id) for cat_id in specification.get("categories", [])]
    
    # Build user message with specification details
    user_message_parts = [
        "# Generator Specification",
        "",
        f"**Newsletter Name:** {specification.get('newsletter_name', 'Unnamed')}",
        f"**Cadence:** {cadence.title()}",
        "",
        "## Selected Deliverables:",
    ]
    
    for cat in selected_categories:
        user_message_parts.append(f"- {cat}")
    
    user_message_parts.extend([
        "",
        "## Selected Regions:",
    ])
    
    for region in specification.get("regions", []):
        user_message_parts.append(f"- {region}")
    
    if historical_reference:
        user_message_parts.extend([
            "",
            "## Historical Reference:",
            "Previous runs for context (do not repeat content):"
        ])
        for ref in historical_reference:
            user_message_parts.append(f"- {ref}")
    
    # Determine lookback period based on cadence
    from datetime import datetime, timedelta
    today = datetime.utcnow()
    if cadence.lower() == "daily":
        lookback_days = 2
        lookback_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        lookback_period = f"Look back {lookback_days} days (since {lookback_date}). Focus on the most recent developments."
    elif cadence.lower() == "weekly":
        lookback_days = 7
        lookback_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        lookback_period = f"Look back {lookback_days} days (since {lookback_date}). Cover the full week period."
    else:  # monthly
        lookback_days = 30
        lookback_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        lookback_period = f"Look back {lookback_days} days (since {lookback_date}). Provide comprehensive coverage of the month."
    
    user_message_parts.extend([
        "",
        "## Instructions:",
        "Generate a newsletter covering the selected deliverables and regions.",
        f"**Lookback Period:** {lookback_period} Only include intelligence items published within this timeframe.",
        "Output must be structured, factual, and relevant to the polyurethane industry.",
        "Do not expand beyond the specified scope.",
        "Present content in a clear, professional format suitable for decision-makers.",
        "",
        "## CRITICAL: Company List Reference - USE THE ATTACHED COMPANY LIST",
        "A comprehensive list of 152+ PU industry companies is available in the attached knowledge base (vector store).",
        "**YOU MUST:**",
        "- FIRST: Use the file_search tool to retrieve the company list from the attached vector store/knowledge base",
        "- The company list file contains 152+ companies with their names, aliases, value chain positions, regions, and status",
        "- Filter the retrieved company list by: (1) Value chain positions matching selected deliverables, (2) Regions matching selected regions",
        "- Search for news about ALL companies in your filtered list - do not skip any companies",
        "- Use the EXACT company names and aliases from the list when searching for news",
        "- Prioritize companies from the list - they are the primary targets for news tracking",
        "- Match companies to deliverables: Use the value chain positions (MDI Producer, TDI Producer, Polyols Producer, Systems, Foam Manufacturer, etc.) to filter relevant companies",
        "- Match companies to regions: Only search for news about companies that operate in the selected regions",
        "- Include news about companies even if they're not explicitly mentioned in your training data - the company list is authoritative",
        "- Verify company status: Only include news about active companies (the list excludes acquired/merged/defunct companies)",
        "- If you find news about a company NOT in the list, you may include it if highly relevant, but ALWAYS prioritize companies from the attached list",
        "- The company list contains 152+ companies across all value chain positions and regions - use it comprehensively",
        "",
        "## CRITICAL: RECENT NEWS ONLY - DATE VERIFICATION REQUIRED",
        f"**CURRENT DATE:** {today.strftime('%Y-%m-%d')}",
        "**ABSOLUTELY CRITICAL RULES:**",
        f"- ONLY include news published between {lookback_date} and {today.strftime('%Y-%m-%d')}",
        "- DO NOT include news from 2020, 2021, 2022, 2023, or any year before the lookback period",
        "- DO NOT include information about companies that ceased operations, were acquired, or no longer exist",
        "- VERIFY company status: If a company was acquired/merged/ceased operations, DO NOT include news about them unless it's about their current entity",
        "- Every news item MUST include the publication date in format: YYYY-MM-DD",
        "- Example format: 'News summary text - Source Name (2025-01-15) (https://real-source.com/actual-article)'",
        "- If you cannot verify the publication date is within the lookback period, DO NOT include that item",
        "- Exclude outdated information: Companies like FoamPartner (acquired in 2020) should NOT appear unless reporting on current entities",
        "",
        "## CRITICAL: Source URLs Required - REAL URLs ONLY",
        "Every news item MUST include a REAL, VERIFIED source URL (full web address) that actually exists and is accessible.",
        "CRITICAL RULES:",
        "- URLs MUST be from actual published sources you have access to",
        "- Do NOT invent, fabricate, or guess URLs",
        "- Do NOT use placeholder URLs (like https://example.com)",
        "- URLs must be from real articles, press releases, or official sources",
        "- If you cannot find a real, accessible URL for an item, DO NOT include that item",
        "- All URLs will be checked - 404 errors are unacceptable and damage credibility",
        "Format examples (using REAL URLs only):",
        "- 'News summary text - Source Name (2025-01-15) (https://real-source.com/actual-article)'",
        "- 'News summary text - Source Name [Source Name](https://real-source.com/actual-article) (2025-01-15)'",
        "- Or include URL directly: 'News summary text (2025-01-15) https://real-source.com/actual-article'",
        "Do NOT include items without REAL, VERIFIED source URLs - all news items must be traceable to actual accessible sources.",
        "",
        "## DATE REQUIREMENT:",
        f"- Every item MUST include publication date in YYYY-MM-DD format",
        f"- Dates MUST be between {lookback_date} and {today.strftime('%Y-%m-%d')}",
        f"- If date is missing or outside this range, DO NOT include the item"
    ])
    
    user_message = "\n".join(user_message_parts)
    
    return {
        "system_instruction": build_system_instruction(),
        "user_message": user_message,
        "specification": specification,
        "cadence": cadence
    }


def execute_assistant(run_package: Dict) -> Dict:
    """
    Execute the OpenAI Assistant with the run package using Assistants API.
    Returns the Assistant's response.
    
    Args:
        run_package: Complete run package from build_run_package()
    
    Returns:
        Dictionary with 'content' (generated text) and 'metadata'
    """
    client = get_openai_client()
    assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
    
    if not client or not assistant_id:
        # Simulate OpenAI response for development
        return {
            "content": f"""
# {run_package['specification'].get('newsletter_name', 'Newsletter')}

**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
**Cadence:** {run_package['cadence'].title()}

## Company News Tracking

### BASF
- **Headline:** BASF announces new MDI capacity expansion in Europe
- **Summary:** BASF plans to increase MDI production capacity by 20% at its European facility to meet growing demand.
- **Source:** Chemical Week

### Covestro
- **Headline:** Covestro reports strong Q4 results in PU segment
- **Summary:** Strong performance driven by increased demand in automotive and construction sectors.
- **Source:** Company Press Release

## Regional Market Monitoring

### EMEA
- **Market Overview:** Polyurethane market shows strong growth in Q4 with 15% YoY increase in demand.
- **Key Drivers:** Automotive sector recovery and construction industry expansion.
- **Outlook:** Continued growth expected in Q1 2025.

---

*This is a simulated response. Connect OpenAI API to generate real content.*
""",
            "metadata": {
                "model": "simulated",
                "tokens_used": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    try:
        # Use OpenAI Assistants API
        # Step 1: Create a thread
        thread = client.beta.threads.create()
        thread_id = thread.id
        
        # Step 2: Add user message to thread
        # Combine system instruction and user message for the Assistant
        # Note: The Assistant's system instructions are configured in the Assistant itself
        # We pass the full specification as the user message
        user_message = f"""{run_package["system_instruction"]}

---

{run_package["user_message"]}"""
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        
        # Step 3: Create and run the Assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Step 4: Poll for completion
        import time
        max_wait_time = 300  # 5 minutes max
        start_time = time.time()
        
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                error_msg = getattr(run_status, "last_error", {}).get("message", "Unknown error")
                raise Exception(f"Assistant run failed: {error_msg}")
            elif run_status.status in ["cancelled", "expired"]:
                raise Exception(f"Assistant run {run_status.status}")
            
            if time.time() - start_time > max_wait_time:
                raise Exception("Assistant run timed out")
            
            time.sleep(2)  # Poll every 2 seconds
        
        # Step 5: Retrieve the Assistant's response
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        
        # Get the latest assistant message
        assistant_messages = [
            msg for msg in messages.data 
            if msg.role == "assistant"
        ]
        
        if not assistant_messages:
            raise Exception("No response from Assistant")
        
        # Extract text content from the message
        latest_message = assistant_messages[0]
        content_parts = []
        
        for content_block in latest_message.content:
            if hasattr(content_block, 'text'):
                content_parts.append(content_block.text.value)
            elif hasattr(content_block, 'text'):
                content_parts.append(str(content_block))
        
        content = "\n\n".join(content_parts) if content_parts else str(latest_message.content)
        
        # Get usage information if available
        usage = getattr(run_status, "usage", None)
        tokens_used = usage.total_tokens if usage else 0
        
        return {
            "content": content,
            "metadata": {
                "model": getattr(run_status, "model", "assistant"),
                "tokens_used": tokens_used,
                "thread_id": thread_id,
                "run_id": run.id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


def validate_output(output: Dict, specification: Dict) -> tuple[bool, List[str]]:
    """
    Validate the Assistant's output.
    
    Checks:
    1. Structural correctness
    2. Alignment with selected deliverables
    3. Absence of out-of-scope content
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    content = output.get("content", "")
    
    # Check 1: Content is not empty
    if not content or len(content.strip()) < 100:
        errors.append("Output content is too short or empty")
    
    # Check 2: Contains newsletter name or specification reference
    newsletter_name = specification.get("newsletter_name", "")
    if newsletter_name and newsletter_name.lower() not in content.lower():
        # Not a hard error, but log it
        pass
    
    # Check 3: Check for selected categories (deliverables)
    from core.taxonomy import PU_CATEGORIES
    category_map = {cat["id"]: cat["name"] for cat in PU_CATEGORIES}
    selected_category_names = [category_map.get(cat_id, "") for cat_id in specification.get("categories", [])]
    
    # At least some categories should be mentioned
    found_categories = sum(1 for cat_name in selected_category_names if cat_name.lower() in content.lower())
    if found_categories == 0 and len(selected_category_names) > 0:
        errors.append("Output does not appear to cover any selected deliverables")
    
    # Check 4: Check for selected regions
    selected_regions = specification.get("regions", [])
    found_regions = sum(1 for region in selected_regions if region.lower() in content.lower())
    if found_regions == 0 and len(selected_regions) > 0:
        errors.append("Output does not appear to cover any selected regions")
    
    # Check 5: Look for obvious out-of-scope content (basic check)
    # In production, this could be more sophisticated
    out_of_scope_keywords = ["pharmaceutical", "food", "textile"]  # Example keywords
    for keyword in out_of_scope_keywords:
        if keyword.lower() in content.lower() and keyword.lower() not in "polyurethane":
            # Not necessarily an error, but could flag for review
            pass
    
    return len(errors) == 0, errors

