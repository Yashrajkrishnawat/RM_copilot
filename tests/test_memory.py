from types import SimpleNamespace as NS

from app.agent.loop import run_agent
from app.agent.memory import memory


class RecordingLLM:
    """Fake LLM that returns scripted replies and records what it was sent."""

    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def chat(self, messages, tools=None):
        self.calls.append(messages)
        return next(self.replies)


def call(name, args):
    return NS(id="c1", function=NS(name=name, arguments=args))


def test_followup_remembers_customer():
    sid = "test-session-1"
    memory.clear(sid)

    llm1 = RecordingLLM([
        NS(content="lookup", tool_calls=None),
        NS(content="", tool_calls=[call("find_customer", '{"rm_id": "RM001", "query": "Ramesh"}')]),
        NS(content="Ramesh is salaried, docs pending.", tool_calls=None),
    ])
    out1 = run_agent("Tell me about Ramesh", "RM001", llm1, session_id=sid)
    assert out1["focus"] == {"lead_id": "L1001", "name": "Ramesh Patel"}

    llm2 = RecordingLLM([
        NS(content="lookup", tool_calls=None),
        NS(content="Pending: salary slips, bank statement, Form 16.", tool_calls=None),
    ])
    out2 = run_agent("what is pending for him?", "RM001", llm2, session_id=sid)

    router_input = llm2.calls[0][1]["content"]
    assert "Ramesh Patel (L1001)" in router_input

    agent_msgs = llm2.calls[1]
    assert "Ramesh Patel" in agent_msgs[0]["content"]
    assert any(m["role"] == "user" and m["content"] == "Tell me about Ramesh" for m in agent_msgs)
    assert out2["focus"]["lead_id"] == "L1001"


def test_switching_rm_starts_fresh():
    sid = "test-session-2"
    memory.clear(sid)
    llm = RecordingLLM([
        NS(content="lookup", tool_calls=None),
        NS(content="", tool_calls=[call("find_customer", '{"rm_id": "RM001", "query": "Ramesh"}')]),
        NS(content="ok", tool_calls=None),
    ])
    run_agent("Tell me about Ramesh", "RM001", llm, session_id=sid)
    assert memory.get(sid, "RM002")["focus"] is None


def test_reset_clears_memory():
    sid = "test-session-3"
    memory.get(sid, "RM001")
    memory.save_turn(sid, "hi", "hello", {"lead_id": "L1001", "name": "Ramesh Patel"})
    memory.clear(sid)
    assert memory.get(sid, "RM001") == {"history": [], "focus": None}