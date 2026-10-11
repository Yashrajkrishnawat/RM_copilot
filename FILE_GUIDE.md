# RM Copilot — File Guide

What each file does, what it should contain, and how the files connect.

## How a request flows

```
RM sends message
      │
      ▼
main.py  ──►  agent/loop.py  ──►  agent/router.py   (which intent? → which tools)
                   │
                   ├──►  llm/client.py               (asks the model what to do)
                   │
                   ├──►  tools/registry.py ──► tools/*.py   (runs the chosen tool)
                   │
                   ▼
            answer + trace + drafts awaiting approval
```

The LLM decides **which tool to call and how to explain the result**. Tools written in plain Python do the actual work.

---

## Root files

| File | Role |
|---|---|
| `.env.example` | Template of all settings (model name, Ollama URL, FOIR cap, ROI). Committed to git. Each developer copies it to `.env`. |
| `.env` | Your local settings. **Never committed** (listed in `.gitignore`). |
| `.gitignore` | Keeps `.venv/`, `.env`, `__pycache__/` and `.pytest_cache/` out of git. |
| `requirements.txt` | Pinned Python dependencies. Regenerate with `pip freeze > requirements.txt` after installing something new. |
| `README.md` | How to set up and run the project. |
| `STATUS.md` | Project status, decisions, progress checklist and open questions. |

---

## `app/` — the application

### `app/__init__.py`
Empty. Marks `app` as a Python package so imports like `from app.config import settings` work.

### `app/main.py` — API entry point
- Creates the FastAPI app.
- `GET /health` returns `{"status": "ok", "model": ...}` so you can check the server is up.
- `POST /chat` accepts `{"rm_id": "...", "message": "..."}`, calls `run_agent()` from `agent/loop.py` and returns its result.
- Contains **no business logic**; it only receives requests and passes them on.
- Run with: `uvicorn app.main:app --reload`

### `app/config.py` — settings
- A `Settings` class (pydantic-settings) that reads values from `.env`.
- Holds: `llm_base_url`, `llm_model`, `llm_temperature`, `llm_num_ctx`, `llm_disable_thinking`, `agent_max_steps`, `ml_scoring_url`, `default_roi`, `foir_cap`.
- Exposes one shared `settings` object that every other file imports.
- **Why:** model or parameter changes only touch `.env`, never code.

---

## `app/llm/` — talking to the model

### `app/llm/client.py`
- An `LLMClient` class wrapping the `openai` library, pointed at Ollama (`http://localhost:11434/v1`).
- One method: `chat(messages, tools=None)` → returns the model's reply (text and/or tool calls).
- Handles model-specific details in one place: low temperature, `num_ctx`, and turning off Qwen3's thinking mode.
- **Why:** this is the only file that knows which LLM is used. Switching to a hosted model means changing `.env`, not the agent.

---

## `app/agent/` — the brain

### `app/agent/prompts.py`
- Holds the prompt text as constants:
  - `SYSTEM_PROMPT`: who the copilot is and its rules (use tools for numbers, never invent figures, messages are drafts only, be concise).
  - `ROUTER_PROMPT`: instructions for classifying a request into one intent.
- **Why:** prompts get tuned often. Keeping them separate from logic makes changes easy to review.

### `app/agent/router.py` — intent routing
- Defines the intent-to-tools map:

  | Intent | Tools exposed |
  |---|---|
  | `triage` | `get_leads`, `score_lead` |
  | `eligibility` | `calc_eligibility` |
  | `checklist` | `doc_checklist` |
  | `followup` | `doc_checklist`, `draft_followup` |
  | `general` | none |

- `route(message, llm)` makes one short LLM call and returns the intent word.
- **Why:** a 4B model is far more reliable choosing between 1–2 tools than 5–6.

### `app/agent/loop.py` — the agent loop
- `run_agent(message, rm_id, llm=None)` is the core function:
  1. Call the router to get the intent and its allowed tools.
  2. Send the system prompt, the RM's message and the tool schemas to the LLM.
  3. If the model asks for a tool, parse its arguments, run the tool, and send the result back.
  4. Repeat until the model gives a final text answer, or `agent_max_steps` is reached.
- Safety checks it must handle:
  - The model calls a tool not allowed for this intent → return an error to the model instead of running it.
  - Arguments are invalid JSON → return an error so the model can retry.
  - Strip any `<think>...</think>` text from the final answer.
- Returns `{intent, answer, trace, approvals}`:
  - `trace`: every tool called, with its arguments and result (for debugging and audit).
  - `approvals`: drafts waiting for the RM to approve.
- The `llm` parameter lets tests pass in a fake LLM.

---

## `app/tools/` — what the agent can do

### `app/tools/__init__.py`
- Imports every tool module (`leads`, `eligibility`, `checklist`, `messaging`).
- **Why:** importing a module runs its `@tool` decorators, which add the tools to the registry. Without this file, the registry would be empty.

### `app/tools/registry.py` — tool plumbing
- `Tool` class: name, description, Pydantic argument model, the function, and a `requires_approval` flag.
  - `spec()` converts the Pydantic model into the JSON schema the LLM needs.
  - `run(raw_args)` validates arguments with Pydantic. On bad input it **returns** an error dict (it does not raise), so the model can correct itself.
- `@tool(...)` decorator registers a function into the global `REGISTRY` dict.
- `specs_for(names)` returns schemas for only the tools the router allowed.
- **Why:** one Pydantic model gives you both the schema for the LLM and input validation.

### `app/tools/eligibility.py` — `calc_eligibility`
- Inputs: monthly income, existing EMI, property value, tenure (years), optional ROI.
- Logic (pure math, no LLM):
  - Max new EMI = income × FOIR cap − existing EMI
  - Loan by income = present value of that EMI over the tenure
  - Loan by LTV = property value × LTV cap (90% up to ₹30L, 80% up to ₹75L, 75% above)
  - Eligible amount = the lower of the two
- Output: eligible amount, EMI, FOIR, LTV and flags (e.g. "Limited by LTV", "High existing obligations").
- ⚠️ FOIR cap and ROI are placeholders; replace them with credit policy values.

### `app/tools/checklist.py` — `doc_checklist`
- Inputs: profile (`salaried`, `self_employed`, `nri`) and the documents already received.
- Combines the base documents (PAN, Aadhaar, photo, property papers) with the profile-specific list.
- Output: required, pending, and whether the file is complete.
- ⚠️ Replace the lists with the credit policy's document matrix.

### `app/tools/leads.py` — `get_leads`, `score_lead`
- `get_leads(rm_id, status=None)`: the RM's leads, optionally filtered by status. Reads `data/leads.json` for now.
- `score_lead(lead_id)`: calls the existing ML scoring service if `ML_SCORING_URL` is set, otherwise uses a simple mock score.
- **Later:** replace the JSON file reads with LOS API calls. Only this file changes.

### `app/tools/messaging.py` — `draft_followup`
- Inputs: customer name, pending documents, language, and the message text the model wrote.
- **Never sends anything.** Returns the draft with status `pending_approval`.
- Marked `requires_approval=True`, so `loop.py` puts its output into `approvals`.
- **Later:** a separate, RM-triggered endpoint will actually send approved drafts via WhatsApp.

---

## `data/`

### `data/leads.json`
- Synthetic leads standing in for the LOS: `lead_id`, `rm_id`, name, employment, income, existing EMI, property value, CIBIL, status, required and received documents.
- **Use only made-up data here.** Never put real customer data in the repo.

---

## `tests/` — automated tests (no Ollama needed)

### `tests/conftest.py`
- Adds the project root to Python's path so tests can `import app`.

### `tests/test_tools.py`
- Tests the pure-Python tools: LTV slabs, eligibility math, the case where obligations exceed FOIR, invalid arguments returning an error, checklist pending logic, and that every tool schema is valid.

### `tests/test_agent_loop.py`
- Tests `run_agent()` using a **fake LLM** that returns scripted replies.
- Covers: a normal eligibility flow, a blocked tool outside the intent, a follow-up landing in `approvals`, and bad JSON arguments.
- **Why:** the agent logic can be tested quickly and repeatably without the model's randomness.

Run all tests: `python -m pytest -q`

---

## `evals/` — measuring the real model

### `evals/cases.jsonl`
- One test case per line: `{"message": ..., "expected_intent": ..., "expected_tools": [...]}`
- Include English, Hindi and Hinglish phrasing. Target 30–50 cases.

### `evals/run_evals.py`
- Runs every case through the **real** model via `run_agent()`.
- Prints ✓/✗ per case and the overall intent accuracy and tool accuracy.
- Run with: `python -m evals.run_evals`
- **Why:** this tells you whether `qwen3:4b` is good enough, and gives numbers to compare models.

### `evals/__init__.py`
- Empty. Makes `python -m evals.run_evals` work.

---

## Tests vs evals

| | `tests/` | `evals/` |
|---|---|---|
| Uses the real LLM? | No (fake LLM) | Yes |
| Checks | Code correctness | Model quality |
| Result | Pass / fail | Accuracy % |
| When to run | Every change | After prompt, model or tool changes |
