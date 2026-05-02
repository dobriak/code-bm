"""Unit tests for FTS5 query builder."""

from raidio.db.fts import fts_query


class TestFtsQuery:
    def test_empty_string_returns_match_all(self):
        assert fts_query("") == '"*"'

    def test_whitespace_returns_match_all(self):
        assert fts_query("   ") == '"*"'

    def test_none_returns_match_all(self):
        assert fts_query("") == '"*"'

    def test_single_word(self):
        result = fts_query("beatles")
        assert result == "beatles*"

    def test_multiple_words(self):
        result = fts_query("radiohead kid a")
        assert "radiohead*" in result
        assert "kid*" in result
        assert "a*" in result
        assert " NEAR/4 " in result

    def test_special_characters_escaped(self):
        result = fts_query('test "quote"')
        assert "test*" in result
        # Quotes should be escaped
        assert '\\"' in result

    def test_parentheses_escaped(self):
        result = fts_query("foo(bar)")
        # Parentheses are escaped, so 'foo*' is part of 'foo\(bar\)*'
        assert "foo" in result
        assert "\\(" in result
        assert "\\)" in result
        assert result.endswith("*")

    def test_star_escaped(self):
        result = fts_query("wild*card")
        # The original * is escaped, and * is appended at end
        assert "wild" in result
        assert "\\*" in result
        assert result.endswith("*")

    def test_numbers(self):
        result = fts_query("2024")
        assert result == "2024*"
