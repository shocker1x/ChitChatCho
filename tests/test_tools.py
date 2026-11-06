import sqlite3
from datetime import date

import pytest

from tools import MockTools


@pytest.fixture
def mock_tools(tmp_path):
    return MockTools(tmp_path / "tools.sqlite3")


def test_search_catalog_and_care_guide(mock_tools):
    results = mock_tools.search_catalog(category="runner", material="wool")
    guide = mock_tools.get_care_guide("shedding")

    assert results["ok"] is True
    assert results["products"]
    assert all(product["category"] == "runner" for product in results["products"])
    assert guide["ok"] is True
    assert "shedding" in guide["guide"].lower()


def test_order_lookup_requires_order_number_and_matching_identity(mock_tools):
    missing_identity = mock_tools.lookup_order("MOCK-ORDER-001")
    wrong_identity = mock_tools.lookup_order("MOCK-ORDER-001", email="wrong@example.invalid")
    verified = mock_tools.lookup_order("MOCK-ORDER-001", postcode="mock 1001")

    assert missing_identity["ok"] is False
    assert wrong_identity["ok"] is False
    assert verified["ok"] is True
    assert verified["order"]["order_id"] == "MOCK-ORDER-001"


def test_track_shipment_and_return_eligibility(mock_tools):
    shipment = mock_tools.track_shipment("MOCK-ORDER-009", email="alex@example.invalid")
    eligible = mock_tools.check_return_eligibility(
        "MOCK-ORDER-017", postcode="MOCK 1002", today=date(2026, 11, 6)
    )
    custom = mock_tools.check_return_eligibility(
        "MOCK-ORDER-020", email="avery@example.invalid", today=date(2026, 11, 6)
    )
    damaged = mock_tools.check_return_eligibility(
        "MOCK-ORDER-033", email="riley@example.invalid", today=date(2026, 11, 6)
    )

    assert shipment["ok"] is True
    assert shipment["shipment"]["tracking_number"] == "MOCKTRACK00000009"
    assert eligible["eligible"] is True
    assert custom["eligible"] is False
    assert "final sale" in custom["reason"]
    assert damaged["eligible"] is True


@pytest.mark.parametrize("tool_name", [
    "issue_refund",
    "issue_store_credit",
    "cancel_order",
    "create_return_label",
    "update_address",
])
def test_risky_tools_require_explicit_confirmation_and_log_failure(mock_tools, tool_name):
    result = _call_risky(mock_tools, tool_name, confirmed=False, idempotency_key="not-confirmed")

    assert result["ok"] is False
    assert "confirmation" in result["error"].lower()
    assert mock_tools.get_tool_logs()[-1]["tool_name"] == tool_name
    assert mock_tools.get_tool_logs()[-1]["result"]["ok"] is False


def test_refund_is_idempotent_logged_and_limited(mock_tools, tmp_path):
    arguments = {
        "order_id": "MOCK-ORDER-001",
        "amount": 100,
        "reason": "mock adjustment",
        "email": "jordan@example.invalid",
        "confirmed": True,
        "idempotency_key": "refund-key-1",
    }
    first = mock_tools.issue_refund(**arguments)
    repeated = mock_tools.issue_refund(**arguments)
    over_limit = mock_tools.issue_refund(
        **{**arguments, "amount": 151, "idempotency_key": "refund-key-2"}
    )

    assert first["ok"] is True
    assert repeated["replayed"] is True
    assert over_limit["ok"] is False
    assert "escalation" in over_limit["error"].lower()
    assert len(mock_tools.get_tool_logs()) == 3
    with sqlite3.connect(tmp_path / "tools.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM financial_transactions").fetchone()[0] == 1


def test_credit_cancel_label_and_address_actions_are_idempotent(mock_tools, tmp_path):
    identity = {"email": "jordan@example.invalid", "confirmed": True}
    credit = mock_tools.issue_store_credit(
        "MOCK-ORDER-001", 25, "mock goodwill", idempotency_key="credit-1", **identity
    )
    credit_again = mock_tools.issue_store_credit(
        "MOCK-ORDER-001", 25, "mock goodwill", idempotency_key="credit-1", **identity
    )
    cancelled = mock_tools.cancel_order(
        "MOCK-ORDER-001", idempotency_key="cancel-1", **identity
    )
    cancelled_again = mock_tools.cancel_order(
        "MOCK-ORDER-001", idempotency_key="cancel-1", **identity
    )
    label = mock_tools.create_return_label(
        "MOCK-ORDER-017", email="casey@example.invalid", confirmed=True, idempotency_key="label-1"
    )
    label_again = mock_tools.create_return_label(
        "MOCK-ORDER-017", email="casey@example.invalid", confirmed=True, idempotency_key="label-1"
    )
    address = mock_tools.update_address(
        "MOCK-ORDER-002", "202 Sample Road", email="casey@example.invalid",
        confirmed=True, idempotency_key="address-1",
    )
    address_again = mock_tools.update_address(
        "MOCK-ORDER-002", "202 Sample Road", email="casey@example.invalid",
        confirmed=True, idempotency_key="address-1",
    )

    assert credit["ok"] is True
    assert credit_again["replayed"] is True
    assert cancelled["ok"] is True
    assert cancelled_again["replayed"] is True
    assert label["ok"] is True
    assert label_again["replayed"] is True
    assert address["ok"] is True
    assert address_again["replayed"] is True
    with sqlite3.connect(tmp_path / "tools.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM financial_transactions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM return_labels").fetchone()[0] == 1
        assert connection.execute("SELECT status FROM orders WHERE order_id='MOCK-ORDER-001'").fetchone()[0] == "cancelled"
        assert connection.execute("SELECT address FROM orders WHERE order_id='MOCK-ORDER-002'").fetchone()[0] == "202 Sample Road"


def test_shipped_orders_cannot_be_cancelled_or_address_changed(mock_tools):
    cancelled = mock_tools.cancel_order(
        "MOCK-ORDER-009", email="alex@example.invalid", confirmed=True, idempotency_key="cancel-shipped"
    )
    changed = mock_tools.update_address(
        "MOCK-ORDER-009", "9 New Road", email="alex@example.invalid",
        confirmed=True, idempotency_key="address-shipped",
    )

    assert cancelled["ok"] is False
    assert changed["ok"] is False


def test_mock_state_persists_when_tool_backend_is_reopened(mock_tools, tmp_path):
    db_path = tmp_path / "tools.sqlite3"
    cancelled = mock_tools.cancel_order(
        "MOCK-ORDER-001", email="jordan@example.invalid", confirmed=True,
        idempotency_key="persist-cancel",
    )
    changed = mock_tools.update_address(
        "MOCK-ORDER-002", "202 Persistent Road", email="casey@example.invalid",
        confirmed=True, idempotency_key="persist-address",
    )

    reopened = MockTools(db_path)
    with sqlite3.connect(db_path) as connection:
        status = connection.execute(
            "SELECT status FROM orders WHERE order_id='MOCK-ORDER-001'"
        ).fetchone()[0]
        address = connection.execute(
            "SELECT address FROM orders WHERE order_id='MOCK-ORDER-002'"
        ).fetchone()[0]

    assert cancelled["ok"] is True
    assert changed["ok"] is True
    assert status == "cancelled"
    assert address == "202 Persistent Road"
    assert reopened.get_tool_logs()


def test_escalation_and_injected_backend_failure_are_logged(tmp_path):
    def fail_every_tool(tool_name, inputs):
        raise RuntimeError(f"synthetic failure in {tool_name}")

    mock_tools = MockTools(tmp_path / "failure.sqlite3", failure_hook=fail_every_tool)
    calls = [
        ("search_catalog", lambda: mock_tools.search_catalog(query="wool")),
        ("lookup_order", lambda: mock_tools.lookup_order("MOCK-ORDER-001", email="jordan@example.invalid")),
        ("track_shipment", lambda: mock_tools.track_shipment("MOCK-ORDER-009", email="alex@example.invalid")),
        ("check_return_eligibility", lambda: mock_tools.check_return_eligibility("MOCK-ORDER-017", email="casey@example.invalid")),
        ("get_care_guide", lambda: mock_tools.get_care_guide("wool")),
        ("issue_refund", lambda: mock_tools.issue_refund("MOCK-ORDER-001", 10, "test", email="jordan@example.invalid", confirmed=True, idempotency_key="fail-refund")),
        ("issue_store_credit", lambda: mock_tools.issue_store_credit("MOCK-ORDER-001", 10, "test", email="jordan@example.invalid", confirmed=True, idempotency_key="fail-credit")),
        ("cancel_order", lambda: mock_tools.cancel_order("MOCK-ORDER-001", email="jordan@example.invalid", confirmed=True, idempotency_key="fail-cancel")),
        ("create_return_label", lambda: mock_tools.create_return_label("MOCK-ORDER-017", email="casey@example.invalid", confirmed=True, idempotency_key="fail-label")),
        ("update_address", lambda: mock_tools.update_address("MOCK-ORDER-001", "New Street", email="jordan@example.invalid", confirmed=True, idempotency_key="fail-address")),
        ("escalate_to_human", lambda: mock_tools.escalate_to_human("A failure summary")),
    ]
    results = [(tool_name, invoke()) for tool_name, invoke in calls]
    escalated = mock_tools.escalate_to_human("Customer requests a mock policy exception.")
    logs = mock_tools.get_tool_logs()

    assert all(not result["ok"] for _, result in results)
    assert all(result["error"] == f"synthetic failure in {tool_name}" for tool_name, result in results)
    assert escalated["ok"] is False
    assert [call["tool_name"] for call in logs] == [tool_name for tool_name, _ in calls] + ["escalate_to_human"]
    assert logs[0]["inputs"]["query"] == "wool"


def _call_risky(mock_tools, tool_name, confirmed, idempotency_key):
    if tool_name == "issue_refund":
        return mock_tools.issue_refund(
            "MOCK-ORDER-001", 10, "test", email="jordan@example.invalid",
            confirmed=confirmed, idempotency_key=idempotency_key,
        )
    if tool_name == "issue_store_credit":
        return mock_tools.issue_store_credit(
            "MOCK-ORDER-001", 10, "test", email="jordan@example.invalid",
            confirmed=confirmed, idempotency_key=idempotency_key,
        )
    if tool_name == "cancel_order":
        return mock_tools.cancel_order(
            "MOCK-ORDER-001", email="jordan@example.invalid",
            confirmed=confirmed, idempotency_key=idempotency_key,
        )
    if tool_name == "create_return_label":
        return mock_tools.create_return_label(
            "MOCK-ORDER-017", email="casey@example.invalid",
            confirmed=confirmed, idempotency_key=idempotency_key,
        )
    return mock_tools.update_address(
        "MOCK-ORDER-001", "202 New Road", email="jordan@example.invalid",
        confirmed=confirmed, idempotency_key=idempotency_key,
    )