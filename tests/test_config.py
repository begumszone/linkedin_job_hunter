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


def test_accepts_up_to_ten_keywords(tmp_path):
    ten = "[" + ", ".join(f"k{i}" for i in range(10)) + "]"
    config = load_config(write(tmp_path, BASE.replace("[finans, IFRS]", ten)))
    assert len(config.searches[0].keywords) == 10


def test_rejects_more_than_ten_keywords(tmp_path):
    eleven = "[" + ", ".join(f"k{i}" for i in range(11)) + "]"
    with pytest.raises(ConfigError, match="en fazla 10"):
        load_config(write(tmp_path, BASE.replace("[finans, IFRS]", eleven)))


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


def test_empty_env_vars_fall_back_to_config_defaults(tmp_path, monkeypatch):
    # Unset GitHub Actions secrets still reach the process as empty strings.
    monkeypatch.setenv("SMTP_PORT", "")
    monkeypatch.setenv("SMTP_HOST", "")
    config = load_config(write(tmp_path, BASE))
    assert config.email.port == 587
    assert config.email.host == "smtp.gmail.com"


def test_env_vars_override_config_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_HOST", "smtp.office365.com")
    config = load_config(write(tmp_path, BASE))
    assert config.email.port == 465
    assert config.email.host == "smtp.office365.com"


def test_blank_sender_falls_back_to_username(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_FROM", "")
    monkeypatch.setenv("SMTP_USERNAME", "me@gmail.com")
    config = load_config(write(tmp_path, BASE))
    assert config.email.sender == "me@gmail.com"


SHARED = """
searches:
  - name: "Benim"
    keywords: [finans]
    recipients_secret: MY_EMAIL
  - name: "Arkadaşım"
    keywords: [denetim]
    recipients_secret: FRIEND_EMAIL
notifications:
  email:
    enabled: true
    recipients: []
"""


def test_recipients_can_come_from_a_named_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_EMAIL", "me@example.com")
    monkeypatch.setenv("FRIEND_EMAIL", "friend@example.com")
    config = load_config(write(tmp_path, SHARED))
    mine, theirs = config.searches
    assert config.recipients_for(mine) == ["me@example.com"]
    assert config.recipients_for(theirs) == ["friend@example.com"]


def test_a_search_with_its_own_recipients_ignores_the_global_list(tmp_path, monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENTS", "me@example.com")
    monkeypatch.setenv("FRIEND_EMAIL", "friend@example.com")
    config = load_config(write(tmp_path, SHARED.replace("recipients_secret: MY_EMAIL", "recipients: []")))
    mine, theirs = config.searches
    assert config.recipients_for(mine) == ["me@example.com"]      # falls back
    assert config.recipients_for(theirs) == ["friend@example.com"]  # not both


def test_disabled_searches_are_skipped(tmp_path):
    text = BASE.replace('    location: "İstanbul, Türkiye"',
                        '    location: "İstanbul, Türkiye"\n    enabled: false')
    config = load_config(write(tmp_path, text))
    assert config.searches[0].enabled is False
    assert config.active_searches() == []


def test_a_search_without_any_recipient_is_rejected(tmp_path):
    text = BASE.replace('    recipients: ["me@example.com"]', "    recipients: []")
    with pytest.raises(ConfigError, match="alıcısı yok"):
        load_config(write(tmp_path, text))


def test_disabled_search_without_recipients_is_not_rejected(tmp_path):
    text = (
        BASE.replace('    recipients: ["me@example.com"]', "    recipients: []")
        .replace('    location: "İstanbul, Türkiye"',
                 '    location: "İstanbul, Türkiye"\n    enabled: false')
    )
    assert load_config(write(tmp_path, text)).active_searches() == []
