"""Customer-support agent using Groq's OpenAI-compatible chat API."""

import json
import os
import uuid
from dataclasses import dataclass, field

from .logger import log_event
from .tools import TOOL_SCHEMAS, execute_tool

DEFAULT_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are a friendly customer-support agent for an online electronics store.

Rules:
- Use lookup_order for anything about a specific order. Ask for the order id if the customer has not given one.
- Use search_faq for policy questions (returns, refunds, shipping, warranty, cancellation).
- Use create_ticket only when you cannot solve the problem with the other tools, and only after you have the customer's email.
- Never invent order details or policies. If a tool returns nothing, say so honestly.
- Keep answers short and clear."""


def _groq_tools() -> list[dict]:
    """Convert the project's Anthropic-style schemas to OpenAI/Groq tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            },
        }
        for schema in TOOL_SCHEMAS
    ]


GROQ_TOOLS = _groq_tools()


@dataclass
class AgentResult:
    answer: str
    messages: list
    tool_calls: list = field(default_factory=list)
    steps: int = 0
    hit_step_limit: bool = False


class SupportAgent:
    def __init__(self, client=None, model: str | None = None, max_steps: int = 6, log_file=None):
        self._client = client
        self.model = model or os.getenv("SUPPORT_AGENT_MODEL", DEFAULT_MODEL)
        self.max_steps = max_steps
        self.log_file = log_file

    @property
    def client(self):
        if self._client is None:
            from groq import Groq

            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "GROQ_API_KEY is missing. Add your Groq API key to the .env file."
                )
            self._client = Groq(api_key=api_key)
        return self._client

    def run(self, user_message: str, history: list | None = None) -> AgentResult:
        run_id = uuid.uuid4().hex[:8]
        messages = list(history or [])
        messages.append({"role": "user", "content": user_message})
        tool_calls: list = []
        log_event("user_message", self.log_file, run_id=run_id, text=user_message)

        for step in range(1, self.max_steps + 1):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[dict(message) for message in messages],
                tools=GROQ_TOOLS,
                tool_choice="auto",
                max_tokens=1024,
            )
            assistant_message = response.choices[0].message
            assistant_dict = assistant_message.model_dump(exclude_none=True)
            messages.append(assistant_dict)

            requested_tools = assistant_message.tool_calls or []
            if not requested_tools:
                answer = (assistant_message.content or "").strip()
                log_event("final_answer", self.log_file, run_id=run_id, steps=step, text=answer)
                return AgentResult(answer, messages, tool_calls, steps=step)

            for call in requested_tools:
                function_name = call.function.name
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be a JSON object")
                except (json.JSONDecodeError, ValueError) as exc:
                    arguments = {}
                    output = {"error": f"Invalid arguments for {function_name}: {exc}"}
                else:
                    log_event(
                        "tool_call", self.log_file, run_id=run_id, step=step,
                        tool=function_name, arguments=arguments,
                    )
                    output = execute_tool(function_name, arguments)

                log_event(
                    "tool_result", self.log_file, run_id=run_id, step=step,
                    tool=function_name, result=output,
                )
                tool_calls.append({
                    "tool": function_name,
                    "arguments": arguments,
                    "result": output,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(output),
                })

        log_event("step_limit_reached", self.log_file, run_id=run_id, max_steps=self.max_steps)
        answer = "Sorry, I couldn't finish that request. I've flagged it for a human agent."
        return AgentResult(answer, messages, tool_calls, steps=self.max_steps, hit_step_limit=True)
