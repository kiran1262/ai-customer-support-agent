import json

from agent import tools


def test_lookup_order_found():
    result = tools.lookup_order("ord-1001")
    assert result["found"] is True
    assert result["order"]["status"] == "shipped"


def test_lookup_order_not_found():
    result = tools.lookup_order("ORD-9999")
    assert result["found"] is False
    assert "ORD-9999" in result["error"]


def test_search_faq_finds_refund_policy():
    result = tools.search_faq("how long does a refund take")
    assert result["matches"]
    assert "refund" in result["matches"][0]["question"].lower()


def test_search_faq_no_match():
    result = tools.search_faq("zzzz qqqq")
    assert result["matches"] == []


def test_create_ticket_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "TICKETS_FILE", tmp_path / "tickets.json")
    result = tools.create_ticket("ravi@example.com", "Broken keyboard", "Keys missing", "high")
    assert result["created"] is True
    saved = json.loads((tmp_path / "tickets.json").read_text())
    assert saved[0]["ticket_id"].startswith("TKT-")
    assert saved[0]["priority"] == "high"


def test_create_ticket_validates_input(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "TICKETS_FILE", tmp_path / "tickets.json")
    assert tools.create_ticket("not-an-email", "x", "y")["created"] is False
    assert tools.create_ticket("a@b.com", "x", "y", "urgent")["created"] is False


def test_execute_tool_handles_unknown_and_bad_args():
    assert "Unknown tool" in tools.execute_tool("nope", {})["error"]
    assert "Bad arguments" in tools.execute_tool("lookup_order", {"wrong": 1})["error"]
