from types import SimpleNamespace as NS

from app.agent.loop import run_agent


class FakeLLM:
    def __init__(self, replies):
        self.replies = iter(replies)

    def chat(self, messages, tools=None):
        return next(self.replies)


def call(name, args):
    return NS(id="c1", function=NS(name=name, arguments=args))


def test_eligibility_flow():
    llm = FakeLLM([
        NS(content="eligibility", tool_calls=None),
        NS(content="", tool_calls=[call("calc_eligibility",
            '{"monthly_income": 65000, "existing_emi": 8000, "property_value": 2800000}')]),
        NS(content="Eligible for about 25.2 lakh.", tool_calls=None),
    ])
    out = run_agent("How much loan?", "RM001", llm)
    assert out["intent"] == "eligibility"
    assert out["trace"][0]["result"]["eligible_amount"] == 2520000


def test_tool_outside_intent_blocked():
    llm = FakeLLM([
        NS(content="eligibility", tool_calls=None),
        NS(content="", tool_calls=[call("triage_leads", '{"rm_id": "RM001"}')]),
        NS(content="done", tool_calls=None),
    ])
    out = run_agent("loan?", "RM001", llm)
    assert "not available" in out["trace"][0]["result"]["error"]


def test_followup_goes_to_approvals():
    llm = FakeLLM([
        NS(content="followup", tool_calls=None),
        NS(content="", tool_calls=[call("draft_followup",
            '{"customer_name": "Ramesh", "pending_docs": ["Bank statement"], "message": "Hi Ramesh..."}')]),
        NS(content="Draft ready for approval.", tool_calls=None),
    ])
    out = run_agent("Remind Ramesh", "RM001", llm)
    assert out["approvals"][0]["status"] == "pending_approval"


def test_bad_json_handled():
    llm = FakeLLM([
        NS(content="checklist", tool_calls=None),
        NS(content="", tool_calls=[call("doc_checklist", "{not json")]),
        NS(content="ok", tool_calls=None),
    ])
    out = run_agent("docs?", "RM001", llm)
    assert "not valid JSON" in out["trace"][0]["result"]["error"]