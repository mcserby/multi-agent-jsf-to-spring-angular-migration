from jsf_migrator.budget import check_quota_error
from jsf_migrator.config import GeminiConfig


def test_clean_exit_is_not_quota():
    patterns = GeminiConfig().quota_patterns
    result = check_quota_error("", "all good", 0, patterns)
    assert result.is_quota_error is False


def test_quota_pattern_detected_case_insensitive():
    patterns = GeminiConfig().quota_patterns
    result = check_quota_error("HTTP 429 Quota exceeded for project", "", 1, patterns)
    assert result.is_quota_error is True
    assert result.matched_pattern is not None


def test_unrelated_failure_is_not_quota():
    patterns = GeminiConfig().quota_patterns
    result = check_quota_error("file not found", "", 1, patterns)
    assert result.is_quota_error is False


def test_resource_exhausted_detected():
    patterns = GeminiConfig().quota_patterns
    result = check_quota_error("status: RESOURCE_EXHAUSTED", "", 1, patterns)
    assert result.is_quota_error is True
