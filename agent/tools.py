"""Tools the agent can call: order lookup, FAQ search, ticket creation."""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TICKETS_FILE = DATA_DIR / "tickets.json"


def _load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def lookup_order(order_id: str) -> dict:
    """Return order details for an order id like ORD-1001."""
    key = order_id.strip().upper()
    order = _load("orders.json").get(key)
    if order is None:
        return {"found": False, "error": f"No order found with id {key}"}
    return {"found": True, "order": order}


def search_faq(query: str, top_k: int = 2) -> dict:
    """Keyword-overlap search over the FAQ. Returns the best matching entries."""
    q = _tokens(query)
    scored = []
    for entry in _load("faq.json"):
        score = len(q & _tokens(entry["question"] + " " + entry["answer"]))
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = [entry for _, entry in scored[:top_k]]
    return {"matches": results} if results else {"matches": [], "note": "No FAQ entry matched"}


def create_ticket(customer_email: str, subject: str, description: str, priority: str = "normal") -> dict:
    """Create a support ticket and persist it to data/tickets.json."""
    if priority not in {"low", "normal", "high"}:
        return {"created": False, "error": "priority must be low, normal or high"}
    if "@" not in customer_email:
        return {"created": False, "error": "A valid customer_email is required"}

    ticket = {
        "ticket_id": "TKT-" + uuid.uuid4().hex[:6].upper(),
        "customer_email": customer_email,
        "subject": subject,
        "description": description,
        "priority": priority,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    tickets = json.loads(TICKETS_FILE.read_text()) if TICKETS_FILE.exists() else []
    tickets.append(ticket)
    TICKETS_FILE.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
    return {"created": True, "ticket": ticket}


TOOL_REGISTRY = {
    "lookup_order": lookup_order,
    "search_faq": search_faq,
    "create_ticket": create_ticket,
}

TOOL_SCHEMAS = [
    {
        "name": "lookup_order",
        "description": "Look up an order by its id (format ORD-####). Returns status, items, tracking and delivery dates.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Order id, e.g. ORD-1001"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "search_faq",
        "description": "Search the FAQ for policy answers (returns, refunds, shipping, warranty, cancellation, tracking).",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The customer's question in plain words"}},
            "required": ["query"],
        },
    },
    {
        "name": "create_ticket",
        "description": "Create a support ticket for a human agent. Use only when the issue cannot be solved with the other tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_email": {"type": "string"},
                "subject": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            },
            "required": ["customer_email", "subject", "description"],
        },
    },
]


def execute_tool(name: str, arguments: dict) -> dict:
    """Run a tool by name. Never raises: errors are returned so the model can recover."""
    func = TOOL_REGISTRY.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**arguments)
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}
    except Exception as exc:  # keep the loop alive on any tool failure
        return {"error": f"{name} failed: {exc}"}
