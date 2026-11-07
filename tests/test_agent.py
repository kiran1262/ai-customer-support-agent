"""Agent-loop tests using a fake Groq client; no API key or network needed."""

import copy
import json
from types import SimpleNamespace

from agent import SupportAgent


def assistant(content=None, tool_calls=None):
    calls = tool_calls or []
    def dump(exclude_none=True):
        result = {"role": "assistant"}
        if content is not None:
            result["content"] = content
        if calls:
            result["tool_calls"] = [
                {"id": c.id, "type": "function", "function": {
                    "name": c.function.name,
                    "arguments": c.function.arguments,
                }} for c in calls
            ]
        return result
    return SimpleNamespace(content=content, tool_calls=calls, model_dump=dump)


def tool_call(id_, name, **arguments):
    return SimpleNamespace(
        id=id_,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def reply(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(copy.deepcopy(kwargs))
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


def make_agent(responses, tmp_path, **kw):
    return SupportAgent(client=FakeClient(responses), log_file=tmp_path / "log.jsonl", **kw)


def test_answers_without_tools(tmp_path):
    agent = make_agent([reply(assistant("Hello! How can I help?"))], tmp_path)
    result = agent.run("hi")
    assert result.answer == "Hello! How can I help?"
    assert result.tool_calls == []
    assert result.steps == 1


def test_calls_tool_then_answers(tmp_path):
    agent = make_agent([
        reply(assistant(tool_calls=[tool_call("t1", "lookup_order", order_id="ORD-1001")])),
        reply(assistant("Your order has shipped via BlueDart.")),
    ], tmp_path)
    result = agent.run("Where is ORD-1001?")
    assert result.steps == 2
    assert result.tool_calls[0]["tool"] == "lookup_order"
    assert result.tool_calls[0]["result"]["found"] is True
    assert "shipped" in result.answer
    second_messages = agent.client.chat.completions.requests[1]["messages"]
    tool_result = second_messages[-1]
    assert tool_result["role"] == "tool"
    assert tool_result["tool_call_id"] == "t1"
    assert json.loads(tool_result["content"])["order"]["order_id"] == "ORD-1001"


def test_tool_calls_are_logged(tmp_path):
    agent = make_agent([
        reply(assistant(tool_calls=[tool_call("t1", "search_faq", query="refund")])),
        reply(assistant("Refunds take 5-7 days.")),
    ], tmp_path)
    agent.run("refund?")
    events = [json.loads(line)["event"] for line in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert events == ["user_message", "tool_call", "tool_result", "final_answer"]


def test_tool_error_is_passed_back_not_raised(tmp_path):
    agent = make_agent([
        reply(assistant(tool_calls=[tool_call("t1", "does_not_exist")])),
        reply(assistant("Sorry, I hit a problem.")),
    ], tmp_path)
    result = agent.run("do something")
    assert "error" in result.tool_calls[0]["result"]
    tool_result = agent.client.chat.completions.requests[1]["messages"][-1]
    assert json.loads(tool_result["content"]).get("error")


def test_step_limit_stops_runaway_loops(tmp_path):
    looping = [reply(assistant(tool_calls=[tool_call(f"t{i}", "search_faq", query="x")])) for i in range(10)]
    agent = make_agent(looping, tmp_path, max_steps=3)
    result = agent.run("loop forever")
    assert result.hit_step_limit is True
    assert result.steps == 3
    assert len(agent.client.chat.completions.requests) == 3


def test_history_is_carried_between_turns(tmp_path):
    agent = make_agent([reply(assistant("First.")), reply(assistant("Second."))], tmp_path)
    first = agent.run("one")
    agent.run("two", first.messages)
    sent = agent.client.chat.completions.requests[1]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"]
