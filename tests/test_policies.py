import json

import pytest

from policies.lookup import POLICY_DATA_PATH, get_policies_for


def test_return_request_returns_standard_and_custom_rules():
    policies = get_policies_for("return_request")

    assert [policy["id"] for policy in policies] == [
        "standard_returns",
        "custom_final_sale",
    ]
    assert all(policy["mock"] for policy in policies)


def test_delivery_estimate_requires_identity_and_supported_dates():
    policies = get_policies_for(" DELIVERY_ESTIMATE ")

    assert {policy["id"] for policy in policies} == {
        "identity_verification",
        "shipment_date_honesty",
    }


def test_refund_authority_includes_limit_and_escalation_rule():
    policies = get_policies_for("refund_or_credit")

    assert len(policies) == 1
    assert "150" in policies[0]["rule"]
    assert "escalated" in policies[0]["rule"]


def test_unknown_situation_is_rejected():
    with pytest.raises(ValueError, match="Unknown situation"):
        get_policies_for("maybe a return")


def test_every_situation_references_existing_mock_rules():
    policy_data = json.loads(POLICY_DATA_PATH.read_text(encoding="utf-8"))
    policy_ids = {policy["id"] for policy in policy_data["rules"]}

    assert policy_data["situations"]
    assert all(
        policy_id in policy_ids
        for policy_list in policy_data["situations"].values()
        for policy_id in policy_list
    )
    assert policy_data["data_notice"].startswith("All policies")