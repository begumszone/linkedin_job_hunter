import pytest

from job_hunter.config import ConfigError, load_config

BASE = """
searches:
  - name: "Finans"
    keywords: [finans, IFRS]
    location: "İstanbul, Türkiye"
notifications:
  email:
    enabled: true
    recipients: ["me@example.com"]
"""


def write(tmp_path, text):
    path = tmp_path / "config.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_a_valid_config(tmp_path):
    config = load_config(write(tmp_path, BASE))
    (search,) = config.searches
    assert search.keywords == ["finans", "IFRS"]
    assert search.match_mode == "any"
    assert config.email.recipients == ["me@example.com"]


def test_rejects_more_than_five_keywords(tmp_path):
    text = BASE.replace("[finans, IFRS]", "[a, b, c, d, e, f]")
    with pytest.raises(ConfigError, match="en fazla 5"):
        load_config(write(tmp_path, text))


def test_rejects_unknown_match_mode(tmp_path):
    text = BASE.replace(
        '    location: "İstanbul, Türkiye"',
        '    location: "İstanbul, Türkiye"\n    match_mode: maybe',
    )
    with pytest.raises(ConfigError, match="match_mode"):
        load_config(write(tmp_path, text))


def test_rejects_email_without_recipients(tmp_path):
    text = BASE.replace('    recipients: ["me@example.com"]', "    recipients: []")
    with pytest.raises(ConfigError, match="alıcı"):
        load_config(write(tmp_path, text))


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="bulunamadı"):
        load_config(tmp_path / "yok.yaml")


def test_recipients_can_come_from_the_environment(tmp_path, monkeypatch):
    text = BASE.replace('    recipients: ["me@example.com"]', "    recipients: []")
    monkeypatch.setenv("EMAIL_RECIPIENTS", "a@example.com, b@example.com")
    config = load_config(write(tmp_path, text))
    assert config.email.recipients == ["a@example.com", "b@example.com"]


def test_env_recipients_are_merged_without_duplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENTS", "me@example.com,other@example.com")
    config = load_config(write(tmp_path, BASE))
    assert config.email.recipients == ["me@example.com", "other@example.com"]
