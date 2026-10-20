import json
import re

import app.tools
from app.agent.memory import memory
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.router import INTENTS, route
from app.config import settings
from app.llm.client import LLMClient
from app.tools.registry import REGISTRY, specs_for

THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def _focus_from(trace):
    """The last customer successfully looked up in this turn becomes the one 'being discussed'."""
    for step in reversed(trace):
        r = step["result"]
        if step["tool"] == "find_customer" and "lead_id" in r and "name" in r:
            return {"lead_id": r["lead_id"], "name": r["name"]}
    return None


def run_agent(user_msg, rm_id, llm=None, session_id=None):
    llm = llm or LLMClient()
    mem = memory.get(session_id, rm_id) if session_id else {"history": [], "focus": None}
    focus = mem["focus"]

    intent = route(user_msg, llm, focus)
    allowed = INTENTS[intent]
    tools = specs_for(allowed)

    system = f"{SYSTEM_PROMPT}\nCurrent RM id: {rm_id}"
    if focus:
        system += f"\nCustomer currently being discussed: {focus['name']} (lead id {focus['lead_id']})."

    messages = [{"role": "system", "content": system}, *mem["history"], {"role": "user", "content": user_msg}]
    trace, approvals = [], []
    answer = "Could not finish within step limit."

    for _ in range(settings.agent_max_steps):
        msg = llm.chat(messages, tools=tools or None)
        calls = msg.tool_calls or []

        if not calls:
            answer = THINK_RE.sub("", msg.content or "").strip()
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in calls],
        })

        for c in calls:
            name = c.function.name
            if name not in allowed:
                result = {"error": f"tool {name} not available for this request"}
            else:
                try:
                    args = json.loads(c.function.arguments or "{}")
                    result = REGISTRY[name].run(args)
                    if REGISTRY[name].requires_approval and "error" not in result:
                        approvals.append(result)
                except json.JSONDecodeError:
                    result = {"error": "arguments were not valid JSON, retry"}

            trace.append({"tool": name, "args": c.function.arguments, "result": result})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": json.dumps(result)})

    new_focus = _focus_from(trace) or focus
    if session_id:
        memory.save_turn(session_id, user_msg, answer, new_focus)

    return {"intent": intent, "answer": answer, "trace": trace, "approvals": approvals, "focus": new_focus}