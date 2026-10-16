import json
import time
from pathlib import Path

from app.agent.loop import run_agent

cases = [json.loads(l) for l in (Path(__file__).parent / "cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
intent_ok = tools_ok = 0
start = time.time()

for c in cases:
    t = time.time()
    out = run_agent(c["message"], "RM001")
    called = {s["tool"] for s in out["trace"]}
    i_ok = out["intent"] == c["expected_intent"]
    t_ok = set(c["expected_tools"]) <= called
    intent_ok += i_ok
    tools_ok += t_ok
    mark = "PASS" if i_ok and t_ok else "FAIL"
    print(f"{mark}  {time.time() - t:5.1f}s  {c['message'][:55]:<55} intent={out['intent']:<12} tools={sorted(called)}")

n = len(cases)
print(f"\nIntent accuracy: {intent_ok}/{n}   Tool accuracy: {tools_ok}/{n}   Total: {time.time() - start:.0f}s")    