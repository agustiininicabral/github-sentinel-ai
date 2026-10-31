from types import SimpleNamespace

from sentinel_api import __main__ as cli


def test_cli_uses_runtime_configuration(monkeypatch):
    captured = {}
    monkeypatch.setattr(cli, "get_settings", lambda: SimpleNamespace(
        host="127.0.0.1", port=8123, environment="production"
    ))
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: captured.update(
        target=args[0], **kwargs
    ))
    cli.run()
    assert captured == {
        "target": "sentinel_api.main:app",
        "host": "127.0.0.1",
        "port": 8123,
        "reload": False,
    }
