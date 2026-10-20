from app.agent.prompts import ROUTER_PROMPT

INTENTS = {
    "triage": ["triage_leads", "score_lead"],
    "lookup": ["find_customer"],
    "eligibility": ["find_customer", "calc_eligibility"],
    "checklist": ["doc_checklist"],
    "followup": ["find_customer", "draft_followup"],
    "general": [],
}


def route(user_msg, llm, focus=None):
    text = f"[Discussing: {focus['name']} ({focus['lead_id']})] {user_msg}" if focus else user_msg
    msg = llm.chat([{"role": "system", "content": ROUTER_PROMPT}, {"role": "user", "content": text}])
    reply = (msg.content or "").lower()
    return next((i for i in INTENTS if i in reply), "general")