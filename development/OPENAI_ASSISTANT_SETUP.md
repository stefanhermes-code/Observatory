# OpenAI Assistant Setup – What You Should See

## Where the instructions live

**Canonical instructions live in the OpenAI Assistant (Dashboard).**  
The app does **not** send the full instructions each run. It sends only the **run specification** (newsletter name, cadence, deliverables, regions, lookback period, date window). The Assistant uses its **Dashboard instructions** plus web search and file_search.

**Reference copy in this repo (for reference only):**

- **`development/OpenAI_Assistant_Instructions_REFERENCE.md`** – Text to paste into the OpenAI Assistant “Instructions” field. It states that the Assistant must:
  - **Search the web** within the given timeframe.
  - Find **PU industry news** with the parameters from the run specification.
  - Find **company news** with the same parameters (using the company list from file_search).
  - Output format: each bullet `Summary - Source (YYYY-MM-DD) https://url`.

Other reference files (V4, minimal, etc.) are legacy or backup; the single reference for “what to put in the Dashboard” is **OpenAI_Assistant_Instructions_REFERENCE.md**.

---

## What you should see in the OpenAI Assistant (Dashboard)

### 1. **Instructions**

Paste the content from **`development/OpenAI_Assistant_Instructions_REFERENCE.md`** (the “Instructions (paste into Dashboard)” section). The instructions must state that the Assistant:

- **Searches the web** within the timeframe given in each run specification.
- Finds **PU industry news** and **company news** matching the specification parameters (deliverables, regions).
- Uses **file_search** to get the company list, filters by spec, then searches for news on those companies.
- Outputs each bullet as `Summary - Source (YYYY-MM-DD) https://url`.

### 2. **Model**

Any supported model (e.g. **gpt-4o**, **gpt-4-turbo**).

### 3. **Tools** (required)

- **File search** – to retrieve the company list from the knowledge base.
- **Web search** – to find real news on the web within the lookback period. Enable this so the Assistant actually searches the web.

### 4. **Knowledge / Files**

- At least one **vector store** attached to the Assistant, containing the **company list** (152+ PU companies, names, value chain positions, regions).

### 5. **Assistant ID**

- Copy the Assistant **ID** (e.g. `asst_xxxxx`) from the OpenAI Dashboard.
- Put it in your app config as **`OPENAI_ASSISTANT_ID`** (Streamlit secrets or `.env`).

---

## What the app sends each run

The app builds a **run specification** and sends it as the user message. It includes:

- Newsletter name, cadence (daily/weekly/monthly).
- Selected deliverables (categories), selected regions.
- Lookback period (date range: e.g. “since 2025-01-24”, “last 7 days”).
- Current date and strict date rules.
- Reminder to use file_search for the company list and to generate the full report (not just describe the plan).

The **detailed behaviour** (search the web, PU industry news, company news, output format) comes from the **Assistant’s Dashboard instructions**, not from the app. So you maintain instructions in the **Dashboard** and keep a **reference copy** in `development/OpenAI_Assistant_Instructions_REFERENCE.md`.

---

## Checklist – “Is my OpenAI agent correctly set up?”

| Check | What to verify |
|-------|----------------|
| **Assistant ID** | Same ID as `OPENAI_ASSISTANT_ID` in secrets / `.env`. |
| **Instructions** | Pasted from `OpenAI_Assistant_Instructions_REFERENCE.md`; they say to **search the web** within the timeframe for PU industry news + company news. |
| **Tools** | **File search** and **Web search** are enabled. |
| **Knowledge** | A **vector store** is attached and contains the **company list** file(s). |
| **Model** | A valid model is selected (e.g. gpt-4o). |

If all of the above are true, your OpenAI agent is correctly set up. The app sends only the run specification; the Assistant uses its Dashboard instructions to search the web and generate the report.
