from common.retention import forced_retention_days


def test_forced_domains_get_fixed_value():
    assert forced_retention_days("alice@businessandtrade.gov.uk") == 42
    assert forced_retention_days("Bob@DSIT.gov.uk") == 42


def test_other_and_lookalike_domains_are_not_forced():
    assert forced_retention_days("carol@other.gov.uk") is None
    assert forced_retention_days("dave@sub.dsit.gov.uk") is None
    assert forced_retention_days("eve@notdsit.gov.uk") is None
    assert forced_retention_days("no-at-sign") is None
