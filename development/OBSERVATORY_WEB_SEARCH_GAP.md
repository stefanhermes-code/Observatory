# PU Observatory: Web Search

## Status

The OpenAI Assistant **can** search the web. When web search is enabled on the Assistant (in the OpenAI Dashboard), it returns real news with the correct format:

- **Summary - Source (YYYY-MM-DD) https://url**
- Example: *"BASF has announced a price increase... - BASF (2024-05-28) https://www.basf.com/global/en/media/..."*

So the product’s core function—find news on the web—is supported **when the same Assistant (with web search enabled) is used**.

## What went wrong in the log

The run that produced “Skipping item - no source found” for every bullet was likely:

1. Using an Assistant that did **not** have web search enabled at that time, so it had no real URLs/dates to cite and produced plain text without " - Source (date) url", or  
2. The same Assistant with web search, but it didn’t use web search for that run (e.g. different prompt or model behaviour).

The parser expects " - Source (date) url". When the Assistant uses web search and cites sources, it outputs that format and items parse correctly. When it doesn’t (no web search or no citations), the parser had nothing to extract—hence the lenient fallback we added (“Source not specified”) so we still show the item.

## What to ensure

1. **Same Assistant in the app**  
   The Observatory app uses an Assistant ID from config/secrets (`OPENAI_ASSISTANT_ID`). Ensure that ID is the **same** Assistant you used for the BASF test (the one with web search enabled). Then every run from the app will have web search available.

2. **Instructions and format**  
   The Assistant is already returning the right format when it uses web search (Summary - Source (date) url). The minimal instructions in the Dashboard and in `core/openai_assistant.py` ask for that format so the parser can extract source and date. No change needed if the Assistant keeps doing that.

3. **If a run still has no source/date**  
   The lenient fallback in `content_pipeline.py` will show those items as “Source not specified” so we don’t drop them. To get real sources every time, the Assistant must have web search enabled and use it for the run (same Assistant ID in the app as in the Dashboard).
