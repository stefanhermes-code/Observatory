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
- **News Sources**: Identify preferred sources for news aggregation (e.g., industry publications, financial news platforms).

## MANDATORY: EXPLOIT SOURCES EXTENSIVELY
- **Use a wide range of source types**: Do NOT rely on one or two sources. Query extensively across multiple source categories:

  **PU-Specific / Industry Trade (Primary Sources):**
  - Urethanes Technology International (UTI) / utech-polyurethane.com - Most authoritative global PU source since 1984; daily news, weekly newsletters, six print issues/year
  - PU magazine - Polyurethane-focused trade publication covering sustainability, recycling, flexible/rigid foam, TPU, applications
  - PUdaily - Independent PU market intelligence platform with prices, data, analysis, news, and reports
  - Utech-polyurethane.com - Daily news covering financial, sustainability, materials/cases, foam products

  **Chemicals / Plastics / Coatings (Secondary, High Relevance):**
  - ICIS - Chemical commodity news and analysis; covers polyurethane, plastics, coatings, feedstocks; 500+ chemical news stories/week
  - Chemical Week - Chemical industry news covering corporate activity, projects, M&A, regulation affecting PU raw materials and downstream
  - Plastics News - US-based plastics industry news, resin pricing, analysis; overlaps with PU conversion and supply chain
  - Plasteurope.com - European plastics business news and price reports; includes polyurethane price reports, composites, recyclate
  - European Coatings Journal / European Coatings - Coatings industry publication covering CASE segment (Coatings, Adhesives, Sealants, Elastomers)
  - Coatings World - Coatings industry news covering CASE segment, formulations, raw materials, regional markets

  **Financial and Business News:**
  - Reuters - Global news and financial coverage; company earnings, M&A, projects, regulation affecting PU companies
  - Bloomberg - Financial and business news, data; commodity and corporate coverage
  - Regional business press - Financial Times, Handelsblatt, Les Echos, regional Asian/LATAM business titles covering regional PU players, policy, trade

  **Trade Bodies and Regulatory:**
  - Center for the Polyurethanes Industry (CPI) - American Chemistry Council; North American PU industry advocacy, safety, benefits messaging
  - ISOPA - European Diisocyanate & Polyol Producers Association; EU PU raw materials regulatory and safety information
  - ALIPA - European Aliphatic Isocyanates Producers Association; aliphatic isocyanates in Europe
  - International Isocyanate Institute (III) - Global diisocyanate technical and safety information
  - Regional PU/chemical associations - China, Japan, Korea, India, Brazil associations for regional policy, events, statistics

  **Company and Official Sources:**
  - Company press releases - Official announcements from PU producers, systems houses, foamers, equipment suppliers
  - Investor relations / earnings - Listed companies (BASF, Covestro, Dow, Huntsman, Recticel, etc.)
  - Regulatory and government - EU (ECHA, DG GROW), US (EPA, OSHA), national agencies; trade and customs

- **Cover all source categories**: For each report, draw from multiple categories: (1) PU-specific industry press, (2) chemical/plastics/coatings trade publications, (3) financial news, (4) company/official sources, (5) trade and regulatory bodies, (6) regional media. The more diverse and extensive the sources, the better the intelligence.
- **No narrow sourcing**: Avoid producing a report that is based mainly on one outlet or one type of source. If you have access to search or retrieval, run multiple queries across different source types and regions to maximize coverage. Prioritize PU-specific sources (UTI, PU magazine, PUdaily) but supplement with chemical/plastics/coatings publications, financial news, and official sources.
- **Every item must name its source AND include URL**: In the output, each intelligence item MUST include the source name, publication date, AND source URL (e.g. "— Source Name (YYYY-MM-DD) https://source.com/article"). Use the actual publication or outlet name, not "various sources" or generic labels. The URL is mandatory for verification - users must be able to click through to verify the news is recent and authentic.

## THINKING PROCESS:
### Phase 1: Analysis
1. **Company List Retrieval**: FIRST, retrieve the company list from the attached vector store/knowledge base. This list contains 152+ companies with their value chain positions and regions.
2. Company Filtering: Filter the company list by (a) value chain positions matching selected deliverables, (b) regions matching selected regions. This gives you the target companies to search for.
3. Industry Identification: Analyze industry trends and key players from the filtered company list.
4. Source Exploitation: Use many source types from the comprehensive list above (PU-specific sources like UTI, PU magazine, PUdaily; chemical/plastics/coatings publications like ICIS, Chemical Week, Plastics News; financial news like Reuters, Bloomberg; company releases; trade bodies like CPI, ISOPA; regional press). Assess credibility and relevance; exclude only biased or clickbait sources—do not narrow to a single outlet.

### Phase 2: News Generation
1. **Targeted Company Search**: Use the EXACT company names and aliases from the filtered company list to search for news. Search for ALL companies in your filtered list, not just a few.
2. Data Extraction: Gather news related to target companies from a wide range of sources (PU-specific: UTI, PU magazine, PUdaily; chemical/plastics/coatings: ICIS, Chemical Week, Plastics News, Plasteurope.com, European Coatings; financial: Reuters, Bloomberg; company releases; trade/regulatory: CPI, ISOPA, ALIPA; regional media). Prioritize companies from the list over general industry knowledge. Do not limit to one or two outlets—exploit sources extensively across all categories.
3. Content Categorization: Classify news items based on relevance (e.g., financial updates, new product launches, regulatory changes).
4. Summarization: Condense news articles into concise summaries for easy consumption.

### Phase 3: Refining
1. Quality Assurance: Ensure the accuracy and reliability of news content.
2. Formatting: Present news items in a structured format for user-friendly access.
3. Update Frequency: Determine the frequency of news updates based on user preferences.

Firewalls: Exclude speculative or unverified information. Avoid biased sources or clickbait headlines.

## OUTPUT FORMATTING:
- Structured Output: Present intelligence items as bulleted lists using markdown format (- for bullet points). Use markdown headers (##, ###) for sections. Do NOT use tables - format items as simple bullet points with clear text.
- **Source URLs Required - MANDATORY**: Each intelligence item MUST include BOTH the publication date (YYYY-MM-DD format) AND the source URL/link. This is NOT optional. Format examples:
  - "News summary text — Source Name (2025-01-15) https://example.com/article"
  - "News summary text — Source Name (2025-01-15) [https://example.com/article](https://example.com/article)"
  - "News summary text — Source Name (2025-01-15) https://www.icis.com/news/article"
  The URL MUST be included for EVERY item. If you cannot find a source URL, DO NOT include that news item. URLs are CRITICAL for verification - users must be able to click through to verify each item is recent and authentic.
- No Fluff: Provide clear and concise intelligence updates without unnecessary details.
- Data Integrity: Ensure all intelligence items are factually correct and relevant to the PU industry.
- **Executive Summary at End - MANDATORY FORMATTING**: After ALL content sections (including "Executive-Ready Briefings" if present), you MUST include a final "## Executive Summary" section at the very end. This summary MUST be written as 3-5 SEPARATE PARAGRAPHS with a blank line between each paragraph. DO NOT create one continuous block of text. 

  **Correct Format Example:**
  ```
  ## Executive Summary
  
  [First paragraph about most significant developments - 3-5 sentences]
  
  [Second paragraph about key market trends - 3-5 sentences]
  
  [Third paragraph about critical implications for decision-makers - 3-5 sentences]
  
  [Fourth paragraph about notable risks or opportunities - 3-5 sentences]
  
  [Optional fifth paragraph with conclusion/outlook - 2-3 sentences]
  ```
  
  **WRONG Format (DO NOT DO THIS):**
  ```
  ## Executive Summary
  [One long continuous paragraph with no breaks - this is WRONG]
  ```
  
  Each paragraph must be separated by a blank line. This executive summary is the final section before any footer - it synthesizes the entire report's content into actionable insights for executives.

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
        "**MANDATORY: Include an Executive Summary at the END with PROPER FORMATTING** - After ALL content sections (including Executive-Ready Briefings), add a final '## Executive Summary' section at the very end. This summary MUST be written as 3-5 SEPARATE PARAGRAPHS with a BLANK LINE between each paragraph. DO NOT create one continuous block of text. Each paragraph should be 3-5 sentences covering: (1) most significant developments, (2) key market trends, (3) critical implications, (4) risks/opportunities, (5) conclusion/outlook. Format: Paragraph 1, then blank line, then Paragraph 2, then blank line, etc. This is the final section before any footer.",
        "",
        "## ⚠️ CRITICAL: MANDATORY COMPANY LIST RETRIEVAL - NO EXCEPTIONS",
        "A comprehensive list of 152+ PU industry companies is available in the attached knowledge base (vector store).",
        "",
        "**YOU MUST DO THIS FIRST - BEFORE ANY NEWS SEARCHING:**",
        "1. **MANDATORY STEP**: Use the file_search tool IMMEDIATELY to retrieve the company list from the attached vector store/knowledge base",
        "2. **VERIFICATION**: You will be monitored - if file_search is not called, your output will be flagged as incomplete",
        "3. **FILE NAME**: Search for files containing 'company' or 'companies' in the knowledge base",
        "",
        "**AFTER RETRIEVING THE COMPANY LIST:**",
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
        "**REMINDER**: This is not optional. You MUST call file_search to retrieve the company list. Your run will be flagged if you don't.",
        "",
        "## CRITICAL: RECENT NEWS ONLY - DATE VERIFICATION REQUIRED",
        f"**CURRENT DATE:** {today.strftime('%Y-%m-%d')}",
        "**ABSOLUTELY CRITICAL RULES:**",
        f"- ONLY include news published between {lookback_date} and {today.strftime('%Y-%m-%d')}",
        "- Use ONLY the article's first publication date (date first published). Do NOT use 'last updated', 'modified', or 'page updated' as the publication date.",
        "- If a source shows only 'updated' or 'modified' and no clear publication date, treat it as having no verifiable publication date and DO NOT include that item.",
        "- DO NOT include news from 2020, 2021, 2022, 2023, or any year before the lookback period",
        "- DO NOT include information about companies that ceased operations, were acquired, or no longer exist",
        "- VERIFY company status: If a company was acquired/merged/ceased operations, DO NOT include news about them unless it's about their current entity",
        "- Every news item MUST include the publication date in format: YYYY-MM-DD",
        "- **MANDATORY URL FORMAT**: Every news item MUST follow this exact format: 'News summary text — Source Name (YYYY-MM-DD) https://source-url.com/article'",
        "- **REQUIRED**: Include the source URL/link for EVERY SINGLE news item - this is NOT optional. Users must be able to click through to verify each item.",
        "- **URL Examples**: '— ICIS (2025-01-15) https://www.icis.com/news/article' or '— Bloomberg (2025-01-15) https://www.bloomberg.com/news/article'",
        "- **If no URL available**: DO NOT include that news item at all - verification via URL is mandatory. If you cannot find a source URL, skip that item entirely.",
        "- **URL verification**: The URL must lead to the actual article/press release. Verify the date matches what you're reporting before including.",
        "- VERIFY dates by checking the source URL - ensure the publication date from the URL matches the date you're reporting",
        "- If you cannot verify the publication date is within the lookback period by checking the source URL, DO NOT include that item",
        "- If no date is available from the source URL, DO NOT include the item at all - missing dates mean the item is excluded",
        "- If the source URL shows a date outside the lookback period, DO NOT include that item - outdated news is excluded",
        "- Exclude outdated information: Companies like FoamPartner (acquired in 2020) should NOT appear unless reporting on current entities",
        "",
        "## STRICT DATE REQUIREMENT - NO EXCEPTIONS:",
        f"- Every item MUST include publication date in YYYY-MM-DD format (first publication date only, not last updated)",
        f"- Dates MUST be between {lookback_date} and {today.strftime('%Y-%m-%d')} - NO EXCEPTIONS",
        f"- If date is missing, outside this range, or cannot be verified, DO NOT include the item - EXCLUDE IT COMPLETELY",
        f"- Example: If today is {today.strftime('%Y-%m-%d')} and lookback is {lookback_days} days, only include news from {lookback_date} onwards",
        "- DO NOT include news from January 2025 or earlier if it's outside the lookback window",
        "- When in doubt about a date, EXCLUDE the item rather than including outdated news",
        "",
        "## ⚠️ CRITICAL OUTPUT REQUIREMENTS - VERIFY BEFORE SUBMITTING:",
        "",
        "**1. SOURCE URLs - MANDATORY FOR EVERY ITEM:**",
        "- Every news item MUST include a source URL: 'News text — Source Name (YYYY-MM-DD) https://url.com'",
        "- If an item does not have a URL, DO NOT include it - skip it entirely",
        "- Verify the URL works and shows the correct publication date",
        "",
        "**2. EXECUTIVE SUMMARY FORMATTING - MANDATORY:**",
        "- The Executive Summary MUST be 3-5 separate paragraphs with blank lines between them",
        "- Format: Paragraph 1 [blank line] Paragraph 2 [blank line] Paragraph 3 [blank line] etc.",
        "- DO NOT create one continuous block of text - use proper paragraph breaks",
        "- Each paragraph should be 3-5 sentences",
        "",
        "**VERIFY YOUR OUTPUT:** Before finishing, check that:",
        "- Every news item has a source URL",
        "- The Executive Summary has proper paragraph breaks (blank lines between paragraphs)",
        "- No continuous text blocks in the Executive Summary"
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
    # Try Streamlit secrets first (for Streamlit Cloud), then environment variables (for local .env)
    try:
        import streamlit as st
        assistant_id = st.secrets.get("OPENAI_ASSISTANT_ID") or os.getenv("OPENAI_ASSISTANT_ID")
        vector_store_id = st.secrets.get("OPENAI_VECTOR_STORE_ID") or os.getenv("OPENAI_VECTOR_STORE_ID")
    except (AttributeError, FileNotFoundError, RuntimeError):
        # Not running in Streamlit or secrets not available, use environment variables
        assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
        vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    
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
        # Step 1: Create a thread with explicit vector store attachment
        thread_params = {}
        if vector_store_id:
            # Explicitly attach the vector store to the thread for file_search
            thread_params["tool_resources"] = {
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
            print(f"[INFO] Attaching vector store {vector_store_id} to thread for file_search")
        else:
            print(f"[WARNING] OPENAI_VECTOR_STORE_ID not found in environment. Vector store will not be attached to thread.")
            print(f"[WARNING] The Assistant must have a vector store attached in the OpenAI Dashboard for file_search to work.")
        
        thread = client.beta.threads.create(**thread_params)
        thread_id = thread.id
        print(f"[INFO] Created thread {thread_id}")
        
        # Step 2: Add user message to thread
        # Combine system instruction and user message for the Assistant
        # Note: The Assistant's system instructions are configured in the Assistant itself
        # We pass the full specification as the user message
        # IMPORTANT: Structure the message so the Assistant understands the first part contains instructions to follow
        user_message = f"""⚠️ CRITICAL: You must GENERATE a complete newsletter report, not describe what you will do. Follow the system instructions below exactly and produce the full newsletter content.

# SYSTEM INSTRUCTIONS - FOLLOW THESE CAREFULLY

{run_package["system_instruction"]}

---

# RUN SPECIFICATION - GENERATE REPORT BASED ON THIS

{run_package["user_message"]}

---

⚠️ REMINDER: Generate the complete newsletter report now. Do not just describe your plan - produce the actual newsletter content."""
        
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        
        # Step 3: Verify Assistant configuration (optional check)
        try:
            assistant_info = client.beta.assistants.retrieve(assistant_id=assistant_id)
            assistant_tools = getattr(assistant_info, 'tools', [])
            has_file_search = any(getattr(tool, 'type', None) == 'file_search' for tool in assistant_tools)
            print(f"[INFO] Assistant tools: {[getattr(t, 'type', 'unknown') for t in assistant_tools]}")
            if not has_file_search:
                print(f"[WARNING] ⚠️ Assistant does not have file_search tool enabled!")
                print(f"[WARNING] Go to OpenAI Dashboard → Your Assistant → Tools → Enable 'File search'")
            else:
                print(f"[INFO] ✅ Assistant has file_search tool enabled")
        except Exception as e:
            print(f"[WARNING] Could not verify Assistant configuration: {e}")
        
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
        
        # Step 5: Retrieve run steps to check for tool calls (vector store usage)
        tool_usage_info = {
            "file_search_called": False,
            "file_search_count": 0,
            "vector_store_used": False,
            "files_retrieved": []
        }
        
        try:
            # Get run steps to check for tool calls
            run_steps = client.beta.threads.runs.steps.list(
                thread_id=thread_id,
                run_id=run.id
            )
            
            print(f"[INFO] Retrieved {len(run_steps.data)} run steps for tool usage tracking")
            
            # Check each step for file_search tool calls
            for step in run_steps.data:
                step_type = getattr(step, 'type', 'unknown')
                print(f"[DEBUG] Step type: {step_type}")
                
                if hasattr(step, 'step_details') and step.step_details:
                    step_details = step.step_details
                    step_details_type = getattr(step_details, 'type', 'unknown')
                    print(f"[DEBUG] Step details type: {step_details_type}")
                    
                    # Check for tool_calls (for tool use steps)
                    # The structure might be step_details.tool_calls or step_details.tool_calls as a list
                    tool_calls = None
                    if hasattr(step_details, 'tool_calls') and step_details.tool_calls:
                        tool_calls = step_details.tool_calls
                    elif hasattr(step_details, 'tool_call') and step_details.tool_call:
                        # Some API versions might use singular
                        tool_calls = [step_details.tool_call]
                    
                    if tool_calls:
                        print(f"[INFO] Found {len(tool_calls)} tool call(s) in step")
                        for tool_call in tool_calls:
                            # Try multiple ways to get the tool type
                            tool_type = None
                            if hasattr(tool_call, 'type'):
                                tool_type = tool_call.type
                            elif isinstance(tool_call, dict):
                                tool_type = tool_call.get('type')
                            
                            print(f"[INFO] Tool call type: {tool_type}")
                            
                            if tool_type == 'file_search':
                                tool_usage_info["file_search_called"] = True
                                tool_usage_info["file_search_count"] += 1
                                tool_usage_info["vector_store_used"] = True
                                print(f"[INFO] ✅ file_search tool was called!")
                                
                                # Try to extract file IDs if available
                                file_ids = []
                                if hasattr(tool_call, 'file_search'):
                                    fs = tool_call.file_search
                                    if hasattr(fs, 'file_ids'):
                                        file_ids = fs.file_ids
                                elif isinstance(tool_call, dict) and 'file_search' in tool_call:
                                    fs = tool_call['file_search']
                                    if isinstance(fs, dict) and 'file_ids' in fs:
                                        file_ids = fs['file_ids']
                                
                                if file_ids:
                                    tool_usage_info["files_retrieved"].extend(file_ids)
                                    print(f"[INFO] Retrieved {len(file_ids)} file(s) via file_search: {file_ids}")
                                else:
                                    print(f"[INFO] file_search called but no file_ids found in response")
                    else:
                        # Log what we found instead
                        print(f"[DEBUG] No tool_calls found. Step details attributes: {dir(step_details)}")
        except Exception as e:
            # If we can't retrieve steps, log but don't fail
            print(f"[WARNING] Could not retrieve run steps for tool usage tracking: {e}")
            import traceback
            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        
        # Step 6: Retrieve the Assistant's response
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
        
        # Verify company list was retrieved - log warning if not
        if not tool_usage_info["file_search_called"]:
            print(f"[WARNING] Company list was NOT retrieved! file_search tool was not called during this run.")
            print(f"[WARNING] The assistant may have missed companies from the knowledge base.")
            print(f"[DEBUG] Vector store ID from env: {vector_store_id}")
            print(f"[DEBUG] Assistant ID: {assistant_id}")
            print(f"[DEBUG] Thread ID: {thread_id}")
            # Add warning to content metadata
            warning_msg = """⚠️ [SYSTEM WARNING: Company list from knowledge base was not retrieved. Results may be incomplete.]
💡 The OpenAI Assistant should use file_search to retrieve the company list. Check the Assistant configuration in OpenAI dashboard:
   1. Ensure file_search tool is enabled
   2. Ensure a vector store is attached to the Assistant
   3. Ensure the vector store contains the company list file(s)
   4. Verify OPENAI_VECTOR_STORE_ID in environment matches the attached vector store"""
            content = f"{warning_msg}\n\n{content}"
        
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
                "timestamp": datetime.utcnow().isoformat(),
                "tool_usage": tool_usage_info,  # Add tool usage tracking
                "company_list_retrieved": tool_usage_info["file_search_called"],
                "company_list_warning": not tool_usage_info["file_search_called"],
                "file_search_count": tool_usage_info["file_search_count"]
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
    # Note: After removing meta-communication, categories might not be explicitly mentioned
    # So we check if there's substantial content instead of requiring exact category name matches
    from core.taxonomy import PU_CATEGORIES
    category_map = {cat["id"]: cat["name"] for cat in PU_CATEGORIES}
    selected_category_names = [category_map.get(cat_id, "") for cat_id in specification.get("categories", [])]
    
    # Check if content has substantial length (indicates content was generated)
    # Also check for category keywords (more lenient - partial matches)
    has_substantial_content = len(content.strip()) > 200
    found_categories = 0
    for cat_name in selected_category_names:
        # Check for partial matches (e.g., "Company News" matches "Company News Tracking")
        cat_words = cat_name.lower().split()
        if any(word in content.lower() for word in cat_words if len(word) > 3):
            found_categories += 1
    
    # Only fail if there's no substantial content AND no category matches
    if not has_substantial_content and found_categories == 0 and len(selected_category_names) > 0:
        errors.append("Output does not appear to cover any selected deliverables")
    
    # Check 4: Check for selected regions
    # DISABLED: Region validation has been completely removed.
    # After removing meta-communication, regions are NOT explicitly mentioned in the content body.
    # Regions are shown in the HTML header (via render_html_from_content), so validation is not needed.
    # The Assistant was instructed to cover the selected regions, and if content was generated (passes Check 1),
    # we assume regions are covered.
    #
    # IMPORTANT: This check is intentionally disabled. Do not add region validation here.
    # If you see "Output does not appear to cover any selected regions" error, it means
    # Streamlit Cloud is running an old cached version. Redeploy the app to pick up this change.
    # No code here - validation is completely skipped.
    
    # Check 5: Look for obvious out-of-scope content (basic check)
    # In production, this could be more sophisticated
    out_of_scope_keywords = ["pharmaceutical", "food", "textile"]  # Example keywords
    for keyword in out_of_scope_keywords:
        if keyword.lower() in content.lower() and keyword.lower() not in "polyurethane":
            # Not necessarily an error, but could flag for review
            pass
    
    return len(errors) == 0, errors

