"""Tests for app/config.py."""

from __future__ import annotations

import warnings

from app.config import load_settings, reload_settings


def _write_settings(tmp_path, content: str):
    path = tmp_path / "settings.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_binance_credentials_loaded_from_env_only(tmp_path, monkeypatch):
    settings_path = _write_settings(
        tmp_path,
        """
app:
  mode: analysis
  kill_switch: true
database:
  path: ./data/test.db
binance:
  base_url: https://api.binance.com
  request_timeout_seconds: 20
  max_retries: 3
  retry_delay_seconds: 1.5
""",
    )
    monkeypatch.setenv("BINANCE_API_KEY", "env-key")
    monkeypatch.setenv("BINANCE_API_SECRET", "env-secret")

    settings = load_settings(settings_path)

    assert settings.binance_api_key == "env-key"
    assert settings.binance_api_secret == "env-secret"
    assert "env-secret" not in repr(settings)


def test_warns_when_binance_credentials_are_in_yaml(tmp_path, monkeypatch):
    settings_path = _write_settings(
        tmp_path,
        """
app:
  mode: analysis
  kill_switch: true
database:
  path: ./data/test.db
binance:
  base_url: https://api.binance.com
  request_timeout_seconds: 20
  max_retries: 3
  retry_delay_seconds: 1.5
  api_key: yaml-key
  api_secret: yaml-secret
""",
    )
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        settings = load_settings(settings_path)

    assert settings.binance_api_key == ""
    assert settings.binance_api_secret == ""
    assert any("Binance API credentials" in str(item.message) for item in caught)


def test_warns_when_telegram_credentials_are_in_yaml(tmp_path):
    settings_path = _write_settings(
        tmp_path,
        """
app:
  mode: analysis
  kill_switch: true
database:
  path: ./data/test.db
binance:
  base_url: https://api.binance.com
  request_timeout_seconds: 20
  max_retries: 3
  retry_delay_seconds: 1.5
alerts:
  notifications:
    telegram:
      enabled: true
      bot_token: yaml-token
      chat_id: yaml-chat
""",
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        load_settings(settings_path)

    assert any("Telegram credentials" in str(item.message) for item in caught)


def test_load_settings_cached_same_object(tmp_path):
    path = _write_settings(
        tmp_path,
        "app:\n  mode: analysis\n  kill_switch: false\ndatabase:\n  path: ./data/test.db\n",
    )
    s1 = load_settings(path)
    s2 = load_settings(path)
    assert s1 is s2


def test_reload_settings_returns_fresh_object(tmp_path):
    path = _write_settings(
        tmp_path,
        "app:\n  mode: analysis\n  kill_switch: false\ndatabase:\n  path: ./data/test.db\n",
    )
    s1 = load_settings(path)
    s2 = reload_settings(path)
    assert s1 is not s2
    assert s1.mode == s2.mode
