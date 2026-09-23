import pytest

from job_hunter.cli import apply_overrides
from job_hunter.config import Config, ConfigError, EmailConfig, NtfyConfig, Search, Settings


def make_config():
    return Config(
        searches=[
            Search(name="Finans / FP&A", keywords=["finans"], recipients=["a@x.com"]),
            Search(name="Pazarlama / CRM", keywords=["marketing"], recipients=["b@x.com"]),
            Search(name="Samet – Sistem Yöneticisi", keywords=["sistem"], recipients=["c@x.com"]),
        ],
        email=EmailConfig(enabled=True),
        ntfy=NtfyConfig(),
        settings=Settings(),
    )


def test_only_search_disables_the_others():
    # A week-long window must not send everyone else a week of backlog.
    config = make_config()
    apply_overrides(config, only_search="Samet")
    assert [s.name for s in config.active_searches()] == ["Samet – Sistem Yöneticisi"]


def test_only_search_ignores_case_and_turkish_letters():
    config = make_config()
    apply_overrides(config, only_search="SİSTEM yöneticisi")
    assert [s.name for s in config.active_searches()] == ["Samet – Sistem Yöneticisi"]


def test_unknown_search_name_is_rejected():
    with pytest.raises(ConfigError, match="Mevcut aramalar"):
        apply_overrides(make_config(), only_search="Yazılım")


def test_hours_and_max_results_overrides():
    config = make_config()
    apply_overrides(config, hours=168, max_results=100)
    assert config.settings.hours == 168
    assert all(s.max_results == 100 for s in config.searches)


def test_no_overrides_leaves_the_config_untouched():
    config = make_config()
    apply_overrides(config)
    assert len(config.active_searches()) == 3
    assert config.settings.hours == 24
