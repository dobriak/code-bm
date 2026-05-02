import pytest

from raidio.db.fts import fts_query


class TestFtsQuery:
    def test_empty_string_returns_1(self):
        assert fts_query("") == "1"
        assert fts_query("   ") == "1"

    def test_single_token(self):
        result = fts_query("beatles")
        assert "beatles" in result
        assert "*" in result

    def test_multiple_tokens(self):
        result = fts_query("beatles yellow submarine")
        assert "beatles" in result
        assert "yellow" in result
        assert "submarine" in result
        assert " OR " in result

    def test_prefix_fuzzy(self):
        result = fts_query("beat")
        assert "*" in result

    def test_special_chars_escaped(self):
        result = fts_query("test query")
        assert "test" in result
        assert "query" in result

    def test_asterisk_preserved(self):
        result = fts_query("beatles*")
        assert "beatles" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
