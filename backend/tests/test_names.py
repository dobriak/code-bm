"""Unit tests for the funny-name generator."""

from __future__ import annotations

from raidio.core.names import ADJECTIVES, SCIENTISTS, generate_name


class TestGenerateName:
    """Tests for generate_name()."""

    def test_returns_string(self):
        result = generate_name()
        assert isinstance(result, str)

    def test_contains_underscore(self):
        result = generate_name()
        assert "_" in result

    def test_format_adjective_scientist(self):
        for _ in range(100):
            result = generate_name()
            parts = result.split("_", 1)
            assert len(parts) == 2
            adjective, scientist = parts
            assert adjective in ADJECTIVES
            assert scientist in SCIENTISTS

    def test_word_lists_nonempty(self):
        assert len(ADJECTIVES) > 50
        assert len(SCIENTISTS) > 20

    def test_no_duplicates_in_word_lists(self):
        assert len(set(ADJECTIVES)) == len(ADJECTIVES)
        assert len(set(SCIENTISTS)) == len(SCIENTISTS)
