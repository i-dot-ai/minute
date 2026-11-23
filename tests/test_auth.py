from unittest.mock import Mock

import pytest

from common import auth
from common.services.exceptions import MissingAuthTokenError


def test_local_auth_uses_configured_email(monkeypatch):
    monkeypatch.setattr(auth.settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(auth.settings, "LOCAL_USER_EMAIL", "jane.smith@businessandtrade.gov.uk")
    result = auth.get_user_info(None)
    assert result.email == "jane.smith@businessandtrade.gov.uk"
    assert result.is_authorised


@pytest.mark.parametrize("environment", ["dev", "preprod", "prod"])
def test_local_identity_cannot_bypass_real_auth(monkeypatch, environment):
    monkeypatch.setattr(auth.settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(auth.settings, "LOCAL_USER_EMAIL", "jane.smith@businessandtrade.gov.uk")
    with pytest.raises(MissingAuthTokenError):
        auth.get_user_info(None)
    authorised = Mock()
    authorise = Mock(return_value=authorised)
    monkeypatch.setattr(auth.auth_client, "get_user_authorisation_info", authorise)
    assert auth.get_user_info("token") is authorised
    authorise.assert_called_once_with("token")
