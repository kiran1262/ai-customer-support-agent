"""Structured logging: every event is printed to the console and appended to logs/agent.jsonl."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "agent.jsonl"

_console = logging.getLogger("support_agent")
if not _console.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", "%H:%M:%S"))
    _console.addHandler(handler)
    _console.setLevel(logging.INFO)


def log_event(event: str, log_file: Path | None = None, **fields) -> dict:
    """Record one event (e.g. tool_call, tool_result, final_answer) and return the record."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        **fields,
    }
    target = log_file or LOG_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    _console.info("%s %s", event, json.dumps(fields, ensure_ascii=False))
    return record
