# RM Copilot — Project Status

_Last updated: 11 Oct 2026_

## What we're building
An agentic AI assistant for Relationship Managers (RMs) that supports the lead-to-login journey:

- **Lead triage** — rank the RM's leads by priority using the existing ML lead-scoring service
- **Eligibility check** — indicative loan amount, EMI, FOIR and LTV
- **Document checklist** — required vs pending documents per customer profile
- **Follow-up drafts** — WhatsApp/SMS reminders in English or Hindi, sent only after RM approval

## Decisions made
| Area | Decision |
|---|---|
| LLM | Self-hosted via **Ollama** (customer data stays in-house) |
| Model (dev) | `qwen3:4b`, with `llama3.2:3b` as a backup to compare |
| LLM interface | OpenAI-compatible client, so a hosted model can be swapped in via `.env` |
| Backend | Python + FastAPI |
| Agent design | One agent with tool calling; an intent router exposes only 1–3 tools per request |
| Calculations | Done in plain Python — the LLM never computes eligibility, it only explains results |
| Customer messages | Drafts only; RM approval required before anything is sent |
| Data | Synthetic leads (`data/leads.json`) until LOS APIs are available |

## Current status
- [x] Use case selected (RM Copilot)
- [x] LLM approach and model chosen
- [x] Project structure created
- [x] Dependencies installed
- [ ] Config + LLM client
- [ ] Tool registry + eligibility calculator (with tests)
- [ ] Checklist, leads and follow-up tools
- [ ] Intent router + agent loop
- [ ] `/chat` API endpoint
- [ ] Eval set (30–50 cases) and first accuracy run

## Project structure
```
app/
  main.py            FastAPI: /health, /chat
  config.py          settings from .env
  llm/client.py      OpenAI-compatible client (Ollama)
  agent/             router.py, loop.py, prompts.py
  tools/             registry.py, leads.py, eligibility.py, checklist.py, messaging.py
data/leads.json      synthetic leads
evals/               cases.jsonl, run_evals.py
tests/               unit tests + agent loop tests with a fake LLM
```

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull qwen3:4b
```

## Constraints & risks
- **Dev hardware:** MacBook Air M3, 8 GB RAM — limited to 3–4B models, one request at a time. Fine for development, not for serving RMs.
- **Small-model reliability:** 3–4B models can pick wrong tools or produce bad JSON. Mitigated by intent routing, few tools per request, schema validation and retries.
- **Hindi quality:** weaker on small local models; to be measured in evals.
- **Placeholder credit parameters:** FOIR cap (50%), ROI (9.5%) and document lists must be replaced with credit policy values.

## Open questions
1. Does the LOS expose APIs for leads and status updates, or do they need to be built?
2. Where will production inference run — on-prem GPU server, India-region cloud GPU, or a hosted API with PII masking?
3. Is WhatsApp Business API already available?
4. Should the copilot be chat-only, proactive nudges, or both?

## Next steps
1. Build config, LLM client and a "hello" test against Ollama
2. Build the tool registry and eligibility calculator with unit tests
3. Build the remaining tools, then the router and agent loop
4. Write the first 30–50 eval cases and measure `qwen3:4b`
