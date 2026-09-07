from job_hunter.matching import matches
from job_hunter.text import fold, tokenize


def test_fold_handles_turkish_casing():
    assert fold("İSTANBUL") == "istanbul"
    assert fold("Finansal Raporlama") == "finansal raporlama"


def test_tokenize_normalizes_punctuation():
    assert tokenize("FP&A") == tokenize("FP & A") == " fp a "


def test_any_mode_needs_one_keyword():
    hits = matches("Kıdemli Finans Uzmanı", ["finans", "FP&A", "IFRS"], mode="any")
    assert hits == ["finans"]


def test_any_mode_reports_every_hit_in_config_order():
    hits = matches("IFRS & FP&A Analisti", ["finans", "FP&A", "IFRS"], mode="any")
    assert hits == ["FP&A", "IFRS"]


def test_all_mode_requires_every_keyword():
    keywords = ["finans", "IFRS"]
    assert matches("Finans Müdürü", keywords, mode="all") == []
    assert matches("Finans / IFRS Raporlama", keywords, mode="all") == keywords


def test_exclude_vetoes_the_posting():
    hits = matches("Finans Stajyeri", ["finans"], mode="any", exclude=["stajyer"])
    assert hits == []


def test_matching_is_case_and_accent_insensitive():
    assert matches("FİNANS UZMANI", ["finans"], mode="any") == ["finans"]


def test_keyword_matches_a_longer_word_it_starts():
    assert matches("Finansal Raporlama Uzmanı", ["finans"], mode="any") == ["finans"]


def test_partial_word_does_not_leak_across_tokens():
    # "IFRS" must not match inside an unrelated word run.
    assert matches("Difrsavunma Uzmanı", ["IFRS"], mode="any") == []
