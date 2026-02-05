# OpenAI Assistant Setup – What You Should See

## Single source of truth: the repo (core/openai_assistant.py)

**All elaborated instructions live in code**, not in the OpenAI Dashboard:

- **Source of truth:** `core/openai_assistant.py`  
  - `build_system_instruction()` → role, rules, source exploitation, company list, etc.  
  - `build_run_package()` → run-specific spec (deliverables, regions, lookback, date rules).
- **Each report run:** The app builds that text and sends it **as the user message** to the Assistant.
- **Effect:** When you edit the `.py` here and deploy, the next report run uses the new instructions. No need to change anything in the Dashboard.

So you **only maintain instructions in the repo**. The Dashboard does **not** need the long PU analyst prompt.

**Reference copies in the workspace (for comparison or backup):**

- `development/OpenAI_Assistant_Instructions_Complete.txt` (V2.0)
- `Instruction Notice OpenAI Agent 05022026.txt` (V3.0)
- **`development/OpenAI_Assistant_Instructions_V4.txt`** – V4 canonical reference; describes the instructions with which the repo works (company list first, source exploitation, date rules). **Repo is not changed**; V4 is documentation only.
- **`development/OpenAI_Assistant_Dashboard_Minimal.txt`** – Minimal text to paste into the OpenAI Dashboard “Instructions” field (one short line).

These reference files are **not** used at runtime. The app uses only what is in `core/openai_assistant.py`.

---

## What you should see in the OpenAI Assistant (Dashboard)

### 1. **Instructions** – keep to one short line

Use a **single short line** so you never maintain instructions in two places, for example:

- *"You are a PU industry news analyst. Follow the instructions and specification in the user message for each run. Use file_search to retrieve the company list from the attached knowledge base when the user message asks for it."*

Do **not** paste the full elaborated instructions here. The app sends the full instructions from `openai_assistant.py` in the user message every run.

### 2. **Model**

- Any supported model (e.g. **gpt-4o**, **gpt-4-turbo**). Pick what your account supports and you prefer.

### 3. **Tools** (required)

- **File search** must be **enabled**.
- The app expects the Assistant to have `file_search` so it can retrieve the company list from the knowledge base. If this tool is missing, the app will still run but will flag that the company list was not retrieved.

### 4. **Knowledge / Files**

- At least one **vector store** must be **attached** to the Assistant.
- That vector store must contain the **company list** file(s) (e.g. file names or content referring to “company” or “companies”, 152+ PU companies with names, value chain positions, regions).
- The app’s user message tells the Assistant to use file_search to get this list; the Assistant can only do that if the vector store is attached here.

### 5. **Assistant ID**

- Copy the Assistant **ID** (e.g. `asst_xxxxx`) from the OpenAI Dashboard.
- Put it in your app config as **`OPENAI_ASSISTANT_ID`** (Streamlit secrets or `.env`). The app uses this to run the correct Assistant.

---

## Checklist – “Is my OpenAI agent correctly set up?”

| Check | What to verify |
|-------|-------------------------------|
| **Assistant ID** | Same ID as `OPENAI_ASSISTANT_ID` in secrets / `.env`. |
| **Tools** | **File search** is enabled. |
| **Knowledge** | A **vector store** is attached and contains the **company list** file(s). |
| **Instructions** | Short note is fine (e.g. “Follow user message; use file_search for company list”). No need to paste the full PU instructions from the repo. |
| **Model** | A valid model is selected (e.g. gpt-4o). |

If all of the above are true, your OpenAI agent is correctly set up. **Detailed instructions** (source exploitation, date rules, value chain, etc.) are applied from **`core/openai_assistant.py`** each time you generate a report. Edit the `.py` in the repo and deploy; no need to maintain the Dashboard instructions.
