from sentinel_api.config import Settings


def test_integration_token_uses_documented_environment_alias(monkeypatch):
    monkeypatch.setenv("SENTINEL_INTEGRATION_TOKEN", "integration-secret")
    settings = Settings(_env_file=None)
    assert settings.integration_token == "integration-secret"


def test_webhook_size_limit_is_bounded():
    settings = Settings(_env_file=None)
    assert settings.max_webhook_bytes == 1_048_576
