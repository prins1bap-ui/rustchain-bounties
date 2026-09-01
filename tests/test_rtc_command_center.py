from scripts.rtc_command_center import LedgerRow, Opportunity, Status, rank_opportunities, totals, validate_ledger


def test_identity_link_required_for_accepted_state():
    rows = [
        LedgerRow(
            key="402-linter",
            issue="#402",
            reward_rtc=100,
            status=Status.ACCEPTED_QUEUED,
            identity_linked=False,
            adjudication_evidence="maintainer comment",
        )
    ]
    errors = validate_ledger(rows)
    assert any("identity evidence required" in error for error in errors)


def test_pending_requires_payout_evidence():
    rows = [
        LedgerRow(
            key="x",
            issue="#x",
            reward_rtc=10,
            status=Status.PENDING_ONCHAIN,
            identity_linked=True,
        )
    ]
    errors = validate_ledger(rows)
    assert any("pending requires payout evidence" in error for error in errors)


def test_superseded_rows_are_removed_from_net_total():
    rows = [
        LedgerRow("old", "#1", 10, Status.SUPERSEDED, supersedes="new"),
        LedgerRow("new", "#1", 10, Status.SUBMITTED, identity_linked=True),
    ]
    result = totals(rows)
    assert result["net_distinct_value"] == 10
    assert result["submitted"] == 10


def test_non_executable_and_unsafe_opportunities_rank_last():
    safe = Opportunity("safe", 20, 0.8, 1, 0, 0.1, 0.1, True, True)
    blocked = Opportunity("blocked", 100, 0.9, 1, 0, 0, 0, False, True)
    unsafe = Opportunity("unsafe", 200, 0.9, 1, 0, 0, 0, True, False)
    ranked = rank_opportunities([blocked, unsafe, safe])
    assert ranked[0].key == "safe"
