# OpenAI Assistant Instructions Version History

## V2 Platform (evidence-based Generator) – 2025
**Status:** The PU Observatory V2 Generator does **not** use the OpenAI Assistant. Report generation is evidence-based: sources + search → candidate_articles → intelligence_writer. No vector store, no file_search. The instruction files below are **legacy** and kept for reference only. See `development/OPENAI_ASSISTANT_V2_STATUS.md`.

---

## Version 2.0 - 2025-01-20 (Legacy)
**Status:** Legacy; not used by current Generator

**Key Changes:**
- Made company list retrieval MANDATORY (not optional)
- Changed company list to be used as enhancement step AFTER initial news detection (not before)
- Clarified that company list is used to verify coverage and enhance results
- Updated Phase 1 to show correct sequence: search news first, then enhance with company list
- Company list is now required to be retrieved using file_search tool after initial news detection

**File:** `development/OpenAI_Assistant_Instructions_Complete.txt`

---

## Version 1.0 - Previous
**Status:** Superseded

**Key Features:**
- Company list was marked as "optional enhancement"
- Instructions were less clear about when/how to use the company list
- Company list could be skipped entirely

---

## How to Update Assistant Instructions

1. Check the version number at the top of `development/OpenAI_Assistant_Instructions_Complete.txt`
2. Compare with what's currently in your OpenAI Assistant dashboard
3. If versions don't match, copy the entire file content to the Assistant's system instructions
4. Update the version number in the Assistant's name or description if needed

## Current Version Check

To see what version is currently in the codebase, check the first few lines of:
`development/OpenAI_Assistant_Instructions_Complete.txt`

Look for: `VERSION: X.X`

