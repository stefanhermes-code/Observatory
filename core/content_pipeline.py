"""
Content pipeline for generating newsletter content.
Fetches, filters, deduplicates, ranks, and assembles newsletter sections.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random


def fetch_content_items(categories: List[str], regions: List[str]) -> List[Dict]:
    """
    Fetch relevant content items from configured PU sources.
    In production, this will connect to actual data sources.
    """
    # Simulate fetching content
    # In production, this would:
    # 1. Connect to RSS feeds, APIs, databases
    # 2. Filter by categories and regions
    # 3. Return structured items
    
    sample_items = [
        {
            "id": "item_1",
            "title": "BASF announces new MDI capacity expansion in Europe",
            "summary": "BASF plans to increase MDI production capacity by 20% at its European facility.",
            "category": "company_news",
            "region": "EMEA",
            "source": "Chemical Week",
            "date": datetime.utcnow().isoformat(),
            "companies": ["BASF"],
            "relevance_score": 0.95
        },
        {
            "id": "item_2",
            "title": "Polyurethane market shows strong growth in Q4",
            "summary": "Regional market analysis indicates 15% YoY growth in PU demand.",
            "category": "regional_monitoring",
            "region": "EMEA",
            "source": "Market Intelligence",
            "date": datetime.utcnow().isoformat(),
            "relevance_score": 0.88
        },
        {
            "id": "item_3",
            "title": "New sustainability regulations impact PU manufacturers",
            "summary": "EU REACH updates require new compliance measures for diisocyanates.",
            "category": "sustainability",
            "region": "EMEA",
            "source": "Regulatory News",
            "date": datetime.utcnow().isoformat(),
            "relevance_score": 0.82
        }
    ]
    
    # Filter by selected categories and regions
    filtered_items = [
        item for item in sample_items
        if item["category"] in categories and item["region"] in regions
    ]
    
    return filtered_items


def deduplicate_items(items: List[Dict]) -> List[Dict]:
    """Remove duplicate items based on title similarity."""
    seen_titles = set()
    unique_items = []
    
    for item in items:
        title_lower = item["title"].lower().strip()
        if title_lower not in seen_titles:
            seen_titles.add(title_lower)
            unique_items.append(item)
    
    return unique_items


def rank_items(items: List[Dict]) -> List[Dict]:
    """Rank items by relevance score and recency."""
    # Sort by relevance score (descending), then by date (descending)
    sorted_items = sorted(
        items,
        key=lambda x: (x.get("relevance_score", 0), x.get("date", "")),
        reverse=True
    )
    
    return sorted_items


def assemble_sections(items: List[Dict], categories: List[str]) -> Dict[str, List[Dict]]:
    """
    Assemble items into sections based on selected categories.
    Returns a dictionary mapping category IDs to lists of items.
    """
    sections = {cat: [] for cat in categories}
    
    for item in items:
        item_category = item.get("category")
        if item_category in sections:
            sections[item_category].append(item)
    
    return sections


def render_html_from_content(
    newsletter_name: str,
    assistant_content: str,
    spec: Dict,
    metadata: Optional[Dict] = None,
    user_email: Optional[str] = None,
    cadence_override: Optional[str] = None
) -> Tuple[str, Dict]:
    """
    Render OpenAI Assistant content as professional HTML report.
    Converts markdown/text content from Assistant into formatted HTML similar to invoice styling.
    """
    from datetime import datetime, timedelta
    import base64
    
    # Calculate lookback period based on cadence (for date filtering)
    cadence = cadence_override or spec.get('frequency', 'monthly')
    if cadence == 'daily':
        lookback_days = 2
    elif cadence == 'weekly':
        lookback_days = 7
    else:  # monthly
        lookback_days = 30
    lookback_date = datetime.utcnow() - timedelta(days=lookback_days)
    from pathlib import Path
    import re
    
    # Get logo for header
    logo_path = Path("Background Documentation/PU Observatory logo V3.png")
    logo_base64 = ""
    if logo_path.exists():
        try:
            with open(logo_path, 'rb') as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                logo_base64 = f"data:image/png;base64,{img_base64}"
        except:
            pass
    
    # Parse assistant content - extract news items with sources
    # Look for patterns like: "Title" - Source (URL) or similar formats
    html_content = assistant_content
    
    # Remove all meta-communication and process explanations from the Assistant's output
    # These are redundant with the HTML header and should not appear in the content
    
    # 1. Remove duplicate title headers (e.g., "HTC Global Market Intelligence" appearing at the start)
    html_content = re.sub(r'^.*?HTC Global Market Intelligence.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE)
    
    # 2. Remove metadata lines: "Generated:", "Frequency:", "Regions:", "Coverage:", "Cadence:", "Scope:"
    html_content = re.sub(r'^.*?(?:Generated|Frequency|Regions|Coverage|Cadence|Scope):\s*.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE)
    
    # 3. Remove "Phase 1:", "Phase 2:", "Phase 3:", "Phase 4:" sections and their content (process explanations)
    # This matches from "Phase X:" to the next major section (## header) or end of content
    html_content = re.sub(r'Phase\s+[0-9]+[:\-].*?(?=\n##|\n###|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    
    # 4. Remove "Notes on Methodology" sections and their content
    html_content = re.sub(r'Notes\s+on\s+Methodology.*?(?=\n##|\n###|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    
    # 5. Remove "CRITICAL:" warnings within content sections
    html_content = re.sub(r'>\s*\n\s*CRITICAL:.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'CRITICAL:.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE)
    
    # 6. Remove explanations about empty results (e.g., "[No qualifying news detected...]")
    html_content = re.sub(r'\[No qualifying.*?\]', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'\[No.*?detected.*?\]', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    
    # 7. Remove methodology explanations (e.g., "The output was generated by systematically...")
    html_content = re.sub(r'The output was generated by.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'Only actionable.*?included.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'News regarding companies.*?excluded.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'If you require early warnings.*?Generator Specification.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'Silence in news.*?monthly window.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    
    # 8. Remove company list retrieval explanations
    html_content = re.sub(r'The attached company list.*?retrieved.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'Filtering was applied.*?regions.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'All news searches.*?filtered companies.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    html_content = re.sub(r'systematically cross-referencing.*?companies.*?(?=\n|$)', '', html_content, flags=re.MULTILINE | re.IGNORECASE | re.DOTALL)
    
    # 9. Remove redundant region coverage lines (e.g., "_Regions covered: ...")
    html_content = re.sub(r'_Regions covered:.*?_', '', html_content, flags=re.MULTILINE | re.IGNORECASE)
    
    # 10. Remove date-only lines that are metadata (e.g., "Nov 19, 2025" standing alone)
    html_content = re.sub(r'^\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\s*$', '', html_content, flags=re.MULTILINE | re.IGNORECASE)
    
    # Clean up multiple consecutive empty lines
    html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)
    
    # Clean up any remaining empty lines at the start
    html_content = re.sub(r'^\s*\n+', '', html_content)
    
    # Convert markdown tables to list format (like other sections) instead of HTML tables
    # Pattern: | Header1 | Header2 | ... followed by |---| and then data rows
    # More robust pattern that handles multi-line tables
    table_pattern = r'\|(.+?)\|\s*\n\s*\|[-:\s\|]+\|\s*\n((?:\|.+\|\s*\n?)+)'
    def convert_table_to_list(match):
        headers = [h.strip() for h in match.group(1).split('|') if h.strip()]
        rows_text = match.group(2).strip()
        rows = [r.strip() for r in rows_text.split('\n') if r.strip() and '|' in r]
        html_list = '<ul class="news-list">\n'
        header_lower = [h.lower() for h in headers]
        for row in rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if cells:
                # Only skip if it's clearly a header row (all cells match header names exactly)
                is_header_row = False
                if len(cells) == len(headers):
                    cells_lower = [c.lower() for c in cells]
                    # Check if all cells match header names (case-insensitive)
                    if all(c in header_lower for c in cells_lower):
                        is_header_row = True
                
                if not is_header_row:
                    # Combine cells into a readable format
                    item_text = ' | '.join(cells)
                    # Remove URLs if present (we don't want links, only dates)
                    item_text_clean = re.sub(r'https?://[^\s\|\)]+', '', item_text)
                    item_text_clean = re.sub(r'www\.[^\s\|\)]+', '', item_text_clean)
                    item_text_clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', item_text_clean)
                    item_text_clean = item_text_clean.strip()
                    # Remove trailing separators
                    item_text_clean = re.sub(r'\s*\|\s*$', '', item_text_clean)
                    # Extract date if available (always try, regardless of URL presence)
                    from datetime import datetime, timedelta
                    date_patterns = [
                        r'\b(\d{4}-\d{2}-\d{2})\b',
                        r'\((\d{4}-\d{2}-\d{2})\)',  # YYYY-MM-DD in parentheses
                        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',
                        r'\b(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',
                    ]
                    news_date = None
                    for pattern in date_patterns:
                        date_match = re.search(pattern, item_text_clean, re.IGNORECASE)
                        if date_match:
                            news_date = date_match.group(1)
                            item_text_clean = item_text_clean.replace(date_match.group(0), '').strip()
                            break
                    
                    # Validate date is within lookback period (based on cadence)
                    formatted_date = ""
                    if news_date:
                        try:
                            if '-' in news_date and len(news_date) == 10:
                                date_obj = datetime.strptime(news_date, "%Y-%m-%d")
                            elif '/' in news_date:
                                parts = news_date.split('/')
                                if len(parts) == 3 and len(parts[2]) == 4:
                                    date_obj = datetime.strptime(news_date, "%m/%d/%Y")
                                else:
                                    date_obj = None
                            else:
                                date_obj = None
                            
                            if date_obj:
                                # Only include dates within the lookback period (not 2 years!)
                                if date_obj >= lookback_date and date_obj <= datetime.utcnow():
                                    # Date is valid and within lookback period, format it
                                    formatted_date = date_obj.strftime("%b %d, %Y")
                                # If date is outside lookback period, don't format it (item will show without date)
                        except:
                            pass
                    
                    # Only show date if it exists
                    date_html = f' <span class="news-date">{formatted_date}</span>' if formatted_date else ''
                    html_list += f'<li><span class="news-item">{item_text_clean}</span>{date_html}</li>\n'
        html_list += '</ul>'
        return html_list
    
    html_content = re.sub(table_pattern, convert_table_to_list, html_content, flags=re.MULTILINE | re.DOTALL)
    
    # Convert markdown headers
    html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
    
    # PRESERVE URLs - convert markdown links to HTML links, keep plain URLs
    # Format: [text](url) -> <a href="url">text</a>
    html_content = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html_content)
    
    # Keep plain URLs as clickable links (convert to <a> tags)
    # Pattern: https:// or http:// followed by non-whitespace
    def url_to_link(match):
        url = match.group(0)
        return f'<a href="{url}" target="_blank">{url}</a>'
    html_content = re.sub(r'https?://[^\s\)\]\>]+', url_to_link, html_content)
    
    # Replace bold
    html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
    
    # Remove section separators (---)
    html_content = re.sub(r'^---+$', '', html_content, flags=re.MULTILINE)
    
    # Replace bullet points and extract URLs
    lines = html_content.split('\n')
    html_lines = []
    in_list = False
    items_found = 0
    items_included = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- ') or stripped.startswith('* '):
            items_found += 1
            if not in_list:
                html_lines.append('<ul class="news-list">')
                in_list = True
            item_text = stripped[2:].strip()
            
            # PRESERVE URLs - extract URLs before processing, then re-add them
            # Extract URLs first (both markdown and plain)
            urls_found = []
            # Extract markdown links [text](url)
            markdown_urls = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', item_text)
            for text, url in markdown_urls:
                urls_found.append(url)
            # Extract plain URLs
            plain_urls = re.findall(r'https?://[^\s\)\]\>]+', item_text)
            urls_found.extend(plain_urls)
            
            # Remove URLs temporarily for source/date extraction (we'll add them back)
            item_text_clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', item_text)
            item_text_clean = re.sub(r'https?://[^\s\)\]\>]+', '', item_text_clean)
            item_text_clean = item_text_clean.strip()
            
            # Extract date and source from the content
            # IMPORTANT: Extract date FIRST before removing anything, then extract source
            # Expected format: "Text - Source Name (2025-01-15)" or "Text - Source Name 2025-01-15"
            
            # Step 1: Extract date FIRST (before removing anything)
            date_patterns = [
                r'\((\d{4}-\d{2}-\d{2})\)',  # YYYY-MM-DD in parentheses (most common format)
                r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD standalone
                r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',  # MM/DD/YYYY or DD/MM/YYYY
                r'\b(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',  # DD MMM YYYY
                r'\b((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b',  # MMM DD, YYYY
            ]
            
            news_date = None
            date_match_obj = None
            for pattern in date_patterns:
                date_match = re.search(pattern, item_text_clean, re.IGNORECASE)
                if date_match:
                    news_date = date_match.group(1)
                    date_match_obj = date_match
                    break
                
            # Step 2: Remove date from text (if found) to prepare for source extraction
            if date_match_obj:
                item_text_clean = item_text_clean.replace(date_match_obj.group(0), '').strip()
            
            # Step 3: Validate date is within lookback period
            from datetime import datetime, timedelta
            formatted_date = ""
            if news_date:
                    try:
                        # Try to parse the date
                        if '-' in news_date and len(news_date) == 10:
                            date_obj = datetime.strptime(news_date, "%Y-%m-%d")
                        elif '/' in news_date:
                            parts = news_date.split('/')
                            if len(parts) == 3 and len(parts[2]) == 4:
                                date_obj = datetime.strptime(news_date, "%m/%d/%Y")
                            else:
                                date_obj = None
                        else:
                            # Try other formats
                            date_obj = None
                        
                        if date_obj:
                            # STRICT VALIDATION: Check if date is within lookback period (based on cadence)
                            # Only include dates within the lookback period, not 2 years!
                            if date_obj >= lookback_date and date_obj <= datetime.utcnow():
                                # Date is valid - format it
                                formatted_date = date_obj.strftime("%b %d, %Y")
                            else:
                                # Date is outside lookback period - EXCLUDE ENTIRE ITEM
                                # This prevents showing outdated news with dates
                                formatted_date = None  # Mark as invalid to skip item
                                news_date = None  # Clear date to skip processing
                    except:
                        # If parsing fails, don't show date and skip item if date was required
                        formatted_date = None
                        news_date = None
            
            # Step 4: Extract source pattern: "Text - Source", "Text : Source", or "Text ; Source"
            # Expected format: "News summary text - Source Name (YYYY-MM-DD) https://url.com"
            # After date removal: "News summary text - Source Name https://url.com"
            # URLs may appear after the source name
            
            source = None
            main_text = item_text_clean
            
            # First, check if there's a URL at the end (after source)
            # URLs should be preserved and added separately
            url_at_end = None
            url_match = re.search(r'\s+(https?://[^\s]+)$', item_text_clean)
            if url_match:
                url_at_end = url_match.group(1)
                item_text_clean = item_text_clean[:url_match.start()].strip()
            
            # Source separator: hyphen, colon, or semicolon only (no en/em dash)
            # Patterns: "Text - Source", "Text : Source", "Text ; Source"
            source_match = re.search(r'\s*[-:;]\s+([A-Za-z0-9][A-Za-z0-9\s&.,\-]+?)(?:\s*$)', item_text_clean)
            if not source_match:
                # Optional: no space after separator "Text: Source" or "Text; Source"
                source_match = re.search(r'\s*[-:;]([A-Za-z0-9][A-Za-z0-9\s&.,\-]+?)(?:\s*$)', item_text_clean)
            
            if source_match:
                source = source_match.group(1).strip()
                # Remove common trailing punctuation that might be part of the source
                source = re.sub(r'[.,;:]+$', '', source).strip()
                main_text = item_text_clean[:source_match.start()].strip()
                # Clean up main text - remove trailing separator and spaces
                main_text = re.sub(r'\s*[-:;]\s*$', '', main_text).strip()
            else:
                # Lenient fallback: no source pattern matched - use whole line as content, generic source
                # So we still show news instead of dropping everything
                main_text = item_text_clean.strip()
                if len(main_text) > 20:  # Only include if there's substantive content
                    source = "Source not specified"
                else:
                    source = None
            
            # If we found a URL at the end, add it to urls_found
            if url_at_end:
                urls_found.append(url_at_end)
            
            # CRITICAL: If a date was found but is outside lookback period, EXCLUDE the entire item
            # This prevents showing outdated news
            if news_date and not formatted_date:
                # Date was found but is invalid/outdated - skip this item completely
                continue
            
            # Require source (or we used fallback with "Source not specified")
            if not source:
                continue
            
            # Date is preferred but if missing, we'll still include the item with source
            # This prevents filtering out all content if Assistant doesn't format dates correctly
            if formatted_date:
                # Both source and date are present - format and display
                date_html = f' <span class="news-date">{formatted_date}</span>'
            else:
                print(f"[DEBUG] Item has source but no valid date: {source}")
                # Still include the item, but without date
                date_html = ""
            # Item passed all checks - include it
            items_included += 1
            
            # Add URL if available
            url_html = ""
            if urls_found:
                # Use the first URL found
                url = urls_found[0]
                url_html = f' <a href="{url}" target="_blank" style="color: #1f77b4; text-decoration: none;">{url}</a>'
            html_lines.append(f'<li><span class="news-item">{main_text}</span> <span class="news-source">- {source}</span>{date_html}{url_html}</li>')
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            # Only skip empty lines or lines that are just separators
            if stripped and stripped != '':
                # Don't skip lines that might contain content
                html_lines.append(line)
    if in_list:
        html_lines.append('</ul>')
    html_content = '\n'.join(html_lines)
    
    # Debug logging for content filtering
    print(f"[DEBUG] Content filtering summary: Found {items_found} news items, included {items_included} items")
    if items_found > 0 and items_included == 0:
        print(f"[WARNING] All {items_found} items were filtered out! Check source/date extraction logic.")
    
    # Extract and format Executive Summary BEFORE wrapping everything in <p> tags
    # NOTE: Headers are already converted to <h2> tags, so we need to match HTML format
    exec_summary_match = re.search(r'(<h2>Executive\s+Summary</h2>)(.*?)(?=<h2>|</p>\s*<div|$)', html_content, flags=re.IGNORECASE | re.DOTALL)
    exec_summary_formatted = None
    exec_summary_start = None
    exec_summary_end = None
    
    if exec_summary_match:
        header = exec_summary_match.group(1)
        content = exec_summary_match.group(2).strip()
        exec_summary_start = exec_summary_match.start()
        exec_summary_end = exec_summary_match.end()
        
        # Remove any existing <p> tags
        content = re.sub(r'</?p>', '', content)
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Split by sentence boundaries (period + space + capital letter)
        sentences = re.split(r'(\.\s+)(?=[A-Z][a-z])', content)
        
        if len(sentences) > 1:
            # Group sentences into paragraphs (3-5 sentences per paragraph)
            paragraphs = []
            current_para = ""
            sentence_count = 0
            
            for i in range(0, len(sentences), 2):
                if i < len(sentences):
                    sentence = sentences[i]
                    if i + 1 < len(sentences):
                        sentence += sentences[i+1]
                    current_para += sentence
                    sentence_count += 1
                    
                    if sentence_count >= 3:
                        if i + 2 >= len(sentences) or sentence_count >= 5:
                            paragraphs.append(current_para.strip())
                            current_para = ""
                            sentence_count = 0
            
            if current_para.strip():
                paragraphs.append(current_para.strip())
        else:
            paragraphs = [content] if content else []
        
        # Format with proper paragraph breaks
        formatted_paras = '\n\n'.join([f'<p>{p.strip()}</p>' for p in paragraphs if p.strip()])
        exec_summary_formatted = f'{header}\n{formatted_paras}'
        
        # Temporarily remove Executive Summary from content so it doesn't get wrapped
        html_content = html_content[:exec_summary_start] + f'<!--EXEC_SUMMARY_PLACEHOLDER-->' + html_content[exec_summary_end:]
    
    # Replace double line breaks with paragraph breaks for rest of content
    html_content = re.sub(r'\n\n+', '</p><p>', html_content)
    html_content = '<p>' + html_content + '</p>'
    
    # Re-insert the formatted Executive Summary (already has <p> tags, so don't wrap it)
    if exec_summary_formatted:
        html_content = html_content.replace('<!--EXEC_SUMMARY_PLACEHOLDER-->', exec_summary_formatted)
    
    # Wrap in professional HTML document (similar to invoice styling)
    html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{newsletter_name}</title>
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ margin: 0; padding: 20px; }}
            @page {{ margin: 1cm; }}
        }}
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
        }}
        .header-logo {{
            max-width: 150px;
            height: auto;
        }}
        .header-title {{
            flex: 1;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: bold;
        }}
        .report-meta {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
            font-size: 0.9em;
        }}
        .report-meta p {{
            margin: 5px 0;
        }}
        h1 {{
            color: #333;
            padding-bottom: 10px;
            margin-top: 30px;
            font-size: 20px;
        }}
        h2 {{
            color: #333;
            margin-top: 30px;
            font-size: 18px;
            font-weight: bold;
        }}
        h3 {{
            color: #555;
            margin-top: 20px;
            font-size: 16px;
        }}
        p {{
            margin: 10px 0;
            line-height: 1.6;
        }}
        ul.news-list {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 8px 0;
            line-height: 1.6;
        }}
        .news-item {{
            font-weight: 500;
        }}
                .news-source {{
                    color: #666;
                    font-size: 0.9em;
                    font-style: italic;
                }}
                .news-date {{
                    color: #666;
                    font-size: 0.9em;
                    margin-left: 8px;
                }}
        a {{
            color: #1f77b4;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        {f'<img src="{logo_base64}" alt="PU Observatory Logo" class="header-logo">' if logo_base64 else ''}
        <div class="header-title">
            <h1>{newsletter_name}</h1>
        </div>
        <div style="width: 120px;"></div>
    </div>
    
            <div class="report-meta">
                <p><strong>Generated:</strong> {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}</p>
                <p><strong>Frequency:</strong> {cadence_override.title() if cadence_override else ("Infinite" if user_email and user_email.lower() == "stefan.hermes@htcglobal.asia" else spec.get('frequency', '').title())}</p>
                <p><strong>Regions:</strong> {', '.join(spec.get('regions', []))}</p>
            </div>
    
    {html_content}
    
    <div class="footer">
        <p><strong>Polyurethane Observatory</strong></p>
        <p>Curated and published by <strong>Global NewsPilot</strong>, a division of HTC Global</p>
    </div>
</body>
</html>"""
    
    # Collect diagnostics for Streamlit UI
    diagnostics = {
        "items_found": items_found,
        "items_included": items_included,
        "items_filtered_out": items_found - items_included,
        "has_exec_summary": exec_summary_formatted is not None,
        "warnings": []
    }
    
    if items_found > 0 and items_included == 0:
        diagnostics["warnings"].append(f"All {items_found} items were filtered out - check source/date extraction")
    elif items_included == 0:
        diagnostics["warnings"].append("No news items found in Assistant output")
    
    if not diagnostics["has_exec_summary"]:
        diagnostics["warnings"].append("Executive Summary section not found")
    
    return html_document, diagnostics


def render_html(newsletter_name: str, sections: Dict[str, List[Dict]], spec: Dict) -> str:
    """
    Render newsletter sections as HTML.
    Returns complete HTML document.
    """
    from core.taxonomy import PU_CATEGORIES
    
    # Get category names
    category_map = {cat["id"]: cat["name"] for cat in PU_CATEGORIES}
    
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>" + newsletter_name + "</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
        "h1 { color: #1f77b4; border-bottom: 3px solid #1f77b4; padding-bottom: 10px; }",
        "h2 { color: #333; margin-top: 30px; border-left: 4px solid #1f77b4; padding-left: 10px; }",
        ".item { margin: 20px 0; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }",
        ".item-title { font-weight: bold; font-size: 1.1em; color: #1f77b4; margin-bottom: 5px; }",
        ".item-summary { color: #666; margin: 10px 0; }",
        ".item-meta { font-size: 0.9em; color: #999; }",
        ".footer { margin-top: 40px; padding-top: 20px; border-top: 2px solid #ddd; text-align: center; color: #666; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{newsletter_name}</h1>",
        f"<p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>",
        f"<p><strong>Frequency:</strong> {spec.get('frequency', '').title()}</p>",
        f"<p><strong>Regions:</strong> {', '.join(spec.get('regions', []))}</p>",
        "<hr>"
    ]
    
    # Render each section
    for category_id, items in sections.items():
        if items:
            category_name = category_map.get(category_id, category_id.replace("_", " ").title())
            html_parts.append(f"<h2>{category_name}</h2>")
            
            for item in items:
                html_parts.append("<div class='item'>")
                html_parts.append(f"<div class='item-title'>{item['title']}</div>")
                html_parts.append(f"<div class='item-summary'>{item['summary']}</div>")
                html_parts.append(f"<div class='item-meta'>Source: {item.get('source', 'Unknown')} | Date: {item.get('date', '')[:10]}</div>")
                html_parts.append("</div>")
    
    # Footer
    html_parts.extend([
        "<div class='footer'>",
        "<p><strong>Polyurethane Industry Observatory</strong></p>",
        "<p>Curated and published by Global NewsPilot, a division of HTC Global</p>",
        "</div>",
        "</body>",
        "</html>"
    ])
    
    return "\n".join(html_parts)


def generate_newsletter(spec: Dict) -> tuple[str, List[Dict]]:
    """
    Complete newsletter generation pipeline.
    Returns: (html_content, items_used)
    """
    # Step 1: Fetch content
    items = fetch_content_items(spec.get("categories", []), spec.get("regions", []))
    
    # Step 2: Deduplicate
    items = deduplicate_items(items)
    
    # Step 3: Rank
    items = rank_items(items)
    
    # Step 4: Assemble sections
    sections = assemble_sections(items, spec.get("categories", []))
    
    # Step 5: Render HTML
    html = render_html(spec.get("newsletter_name", "Newsletter"), sections, spec)
    
    return html, items

