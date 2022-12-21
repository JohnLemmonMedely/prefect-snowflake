from unittest.mock import MagicMock

import pytest
from pydantic import SecretBytes, SecretStr

from prefect_snowflake.credentials import InvalidPemFormat, SnowflakeCredentials


@pytest.fixture
def snowflake_auth(monkeypatch):
    auth_mock = MagicMock()
    auth_mock.authenticate.side_effect = lambda: "authenticated"
    monkeypatch.setattr("snowflake.connector.connection.Auth", auth_mock)


def test_snowflake_credentials_init(credentials_params):
    snowflake_credentials = SnowflakeCredentials(**credentials_params)
    actual_credentials_params = snowflake_credentials.dict()
    for param in credentials_params:
        actual = actual_credentials_params[param]
        expected = credentials_params[param]
        if isinstance(actual, SecretStr):
            actual = actual.get_secret_value()
        assert actual == expected


def test_snowflake_credentials_validate_auth_kwargs(credentials_params):
    credentials_params_missing = credentials_params.copy()
    credentials_params_missing.pop("password")
    with pytest.raises(ValueError, match="One of the authentication keys"):
        SnowflakeCredentials(**credentials_params_missing)


def test_snowflake_credentials_validate_token_kwargs(credentials_params):
    credentials_params_missing = credentials_params.copy()
    credentials_params_missing.pop("password")
    credentials_params_missing["authenticator"] = "oauth"
    with pytest.raises(ValueError, match="If authenticator is set to `oauth`"):
        SnowflakeCredentials(**credentials_params_missing)

    # now test if passing both works
    credentials_params_missing["token"] = "some_token"
    assert SnowflakeCredentials(**credentials_params_missing)


def test_snowflake_credentials_validate_okta_endpoint_kwargs(credentials_params):
    credentials_params_missing = credentials_params.copy()
    credentials_params_missing.pop("password")
    credentials_params_missing["authenticator"] = "okta_endpoint"
    with pytest.raises(ValueError, match="If authenticator is set to `okta_endpoint`"):
        SnowflakeCredentials(**credentials_params_missing)

    # now test if passing both works
    credentials_params_missing["endpoint"] = "https://account_name.okta.com"
    assert SnowflakeCredentials(**credentials_params_missing)


def test_snowflake_private_credentials_init(private_credentials_params):
    snowflake_credentials = SnowflakeCredentials(**private_credentials_params)
    actual_credentials_params = snowflake_credentials.dict()
    for param in private_credentials_params:
        actual = actual_credentials_params[param]
        expected = private_credentials_params[param]
        if isinstance(actual, (SecretStr, SecretBytes)):
            actual = actual.get_secret_value()
        assert actual == expected


def test_snowflake_private_credentials_invalid_certificate(private_credentials_params):
    private_credentials_params["private_key"] = "---- INVALID CERTIFICATE ----"
    with pytest.raises(InvalidPemFormat):
        SnowflakeCredentials(**private_credentials_params)


def test_snowflake_private_credentials_malformed_certificate(
    private_credentials_params, private_malformed_credentials_params
):
    correct = SnowflakeCredentials(**private_credentials_params)
    malformed = SnowflakeCredentials(**private_malformed_credentials_params)
    c1 = correct.resolve_private_key()
    c2 = malformed.resolve_private_key()
    assert isinstance(c1, bytes)
    assert isinstance(c2, bytes)
    assert c1 == c2


def test_snowflake_credentials_validate_private_key_password(
    private_credentials_params,
):
    credentials_params_missing = private_credentials_params.copy()
    password = credentials_params_missing.pop("password")
    private_key = credentials_params_missing.pop("private_key")
    assert password == "letmein"
    assert isinstance(private_key, bytes)
    # Test cert as string
    credentials = SnowflakeCredentials(**private_credentials_params)
    assert credentials.resolve_private_key() is not None


def test_snowflake_credentials_validate_private_key_invalid(private_credentials_params):
    credentials_params_missing = private_credentials_params.copy()
    private_key = credentials_params_missing.pop("private_key")
    assert isinstance(private_key, bytes)
    assert private_key.startswith(b"----")
    with pytest.raises(ValueError, match="Bad decrypt. Incorrect password?"):
        credentials = SnowflakeCredentials(**private_credentials_params)
        credentials.password = "_wrong_password"
        assert credentials.resolve_private_key() is not None


def test_snowflake_credentials_validate_private_key_unexpected_password(
    private_credentials_params,
):
    credentials_params_missing = private_credentials_params.copy()
    private_key = credentials_params_missing.pop("private_key")
    assert isinstance(private_key, bytes)
    assert private_key.startswith(b"----")
    with pytest.raises(
        TypeError, match="Password was not given but private key is encrypted"
    ):
        credentials = SnowflakeCredentials(**private_credentials_params)
        credentials.password = None
        assert credentials.resolve_private_key() is not None


def test_snowflake_credentials_validate_private_key_no_pass_password(
    private_no_pass_credentials_params,
):
    credentials_params_missing = private_no_pass_credentials_params.copy()
    password = credentials_params_missing.pop("password")
    private_key = credentials_params_missing.pop("private_key")
    assert password == "letmein"
    assert isinstance(private_key, bytes)
    assert private_key.startswith(b"----")

    with pytest.raises(
        TypeError, match="Password was given but private key is not encrypted"
    ):
        credentials = SnowflakeCredentials(**private_no_pass_credentials_params)
        assert credentials.resolve_private_key() is not None


def test_snowflake_credentials_validate_private_key_is_pem(
    private_no_pass_credentials_params,
):
    private_no_pass_credentials_params["private_key"] = "_invalid_key_"
    with pytest.raises(InvalidPemFormat):
        credentials = SnowflakeCredentials(**private_no_pass_credentials_params)
        assert credentials.resolve_private_key() is not None


def test_snowflake_credentials_validate_private_key_is_pem_bytes(
    private_no_pass_credentials_params,
):
    private_no_pass_credentials_params["private_key"] = "_invalid_key_"
    with pytest.raises(InvalidPemFormat):
        credentials = SnowflakeCredentials(**private_no_pass_credentials_params)
        assert credentials.resolve_private_key() is not None
