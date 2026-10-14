import json
import re

import app.tools
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.router import INTENTS, route
from app.config import settings
from app.llm.client import LLMClient
from app.tools.registry import REGISTRY, specs_for


THINK_RE = re.compile(r"<think>.*</think>",re.S)

def run_agent(user_msg, rm_id, llm = None):
    llm = llm or LLMClient()
    intent = route(user_msg, llm)
    allowed = INTENTS[intent]
    tools = specs_for(allowed)

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\nCurrent RM id: {rm_id}"},
        {"role": "user", "content": user_msg},
    ]
    trace, approvals = [], []

    for _ in range(settings.agent_max_steps):
        msg = llm.chat(messages, tools=tools or None)
        calls = msg.tool_calls or []

        if not calls:
            answer = THINK_RE.sub("", msg.content or "").strip()
            return {"intent": intent, "answer": answer, "trace": trace, "approvals": approvals}

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

    return {"intent": intent, "answer": "Could not finish within step limit.", "trace": trace, "approvals": approvals}