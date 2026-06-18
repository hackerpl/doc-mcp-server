"""Unit tests for ContentMatcher module."""

import pytest

from ftp_doc_reader.matcher import ContentMatcher
from ftp_doc_reader.models import MatchSnippet


class TestContentMatcherBasic:
    """Basic matching behavior tests."""

    def test_no_match_returns_empty_list(self):
        """When query is not found in text, return empty list."""
        matcher = ContentMatcher("hello")
        result = matcher.match("world foo bar")
        assert result == []

    def test_empty_text_returns_empty_list(self):
        """When text is empty, return empty list."""
        matcher = ContentMatcher("hello")
        result = matcher.match("")
        assert result == []

    def test_empty_query_returns_empty_list(self):
        """When query is empty, return empty list."""
        matcher = ContentMatcher("")
        result = matcher.match("some text here")
        assert result == []

    def test_single_match(self):
        """Find a single occurrence of the query."""
        matcher = ContentMatcher("world")
        result = matcher.match("hello world!")
        assert len(result) == 1
        assert isinstance(result[0], MatchSnippet)
        assert "world" in result[0].text
        assert result[0].position == 6

    def test_case_insensitive_matching(self):
        """Matching should be case-insensitive."""
        matcher = ContentMatcher("Hello")
        result = matcher.match("HELLO world hello HELLO")
        assert len(result) == 3
        # All matches should contain a form of "hello"
        for snippet in result:
            assert "hello" in snippet.text.lower()

    def test_case_insensitive_query_uppercase(self):
        """Query in uppercase should match lowercase text."""
        matcher = ContentMatcher("PYTHON")
        result = matcher.match("I love python programming")
        assert len(result) == 1
        assert "python" in result[0].text

    def test_multiple_matches(self):
        """Find multiple occurrences."""
        matcher = ContentMatcher("cat")
        text = "The cat sat on the mat. Another cat appeared. The cat left."
        result = matcher.match(text)
        assert len(result) == 3


class TestContentMatcherSnippetLimit:
    """Tests for the 5-snippet maximum limit."""

    def test_max_five_snippets(self):
        """Should return at most 5 snippets even if more matches exist."""
        matcher = ContentMatcher("x")
        # Create text with many occurrences of 'x'
        text = " ".join(["x"] * 100)
        result = matcher.match(text)
        assert len(result) == 5

    def test_exactly_five_matches(self):
        """Return exactly 5 snippets when there are exactly 5 matches."""
        matcher = ContentMatcher("find")
        text = "find " * 5 + "no more"
        result = matcher.match(text)
        assert len(result) == 5


class TestContentMatcherContext:
    """Tests for context snippet generation."""

    def test_context_100_chars_before_and_after(self):
        """Snippet should include up to 100 characters before and after match."""
        before = "A" * 100
        after = "B" * 100
        text = before + "KEYWORD" + after
        matcher = ContentMatcher("KEYWORD")
        result = matcher.match(text)
        assert len(result) == 1
        snippet = result[0].text
        # Should contain full before + keyword + full after
        assert "A" * 100 in snippet
        assert "KEYWORD" in snippet
        assert "B" * 100 in snippet

    def test_match_at_start_of_text(self):
        """Match at the very beginning - less than 100 chars before."""
        text = "hello" + "x" * 200
        matcher = ContentMatcher("hello")
        result = matcher.match(text)
        assert len(result) == 1
        # No ellipsis at start since match is at position 0
        assert not result[0].text.startswith("...")
        # Should have ellipsis at end (text continues)
        assert result[0].text.endswith("...")

    def test_match_at_end_of_text(self):
        """Match at the very end - less than 100 chars after."""
        text = "x" * 200 + "hello"
        matcher = ContentMatcher("hello")
        result = matcher.match(text)
        assert len(result) == 1
        # Should have ellipsis at start (text before)
        assert result[0].text.startswith("...")
        # No ellipsis at end since match is at the end
        assert not result[0].text.endswith("...")

    def test_ellipsis_when_text_before_snippet(self):
        """Add '...' prefix when there's text before the snippet start."""
        # Place match far enough from start that context is truncated
        text = "Z" * 200 + "TARGET" + "Z" * 200
        matcher = ContentMatcher("TARGET")
        result = matcher.match(text)
        assert len(result) == 1
        assert result[0].text.startswith("...")
        assert result[0].text.endswith("...")

    def test_no_ellipsis_for_short_text(self):
        """No ellipsis when text is short enough to fit entirely."""
        text = "short text with word inside"
        matcher = ContentMatcher("word")
        result = matcher.match(text)
        assert len(result) == 1
        assert not result[0].text.startswith("...")
        assert not result[0].text.endswith("...")

    def test_snippet_length_bounded(self):
        """Snippet should not exceed 200 + query_len + 6 (ellipsis) chars."""
        text = "X" * 500 + "QUERY" + "Y" * 500
        matcher = ContentMatcher("QUERY")
        result = matcher.match(text)
        assert len(result) == 1
        # Max length: "..." (3) + 100 + 5 (query) + 100 + "..." (3) = 211
        assert len(result[0].text) <= 200 + len("QUERY") + 6


class TestContentMatcherPosition:
    """Tests for correct position reporting."""

    def test_position_is_character_index(self):
        """Position should be the character index of the match in original text."""
        text = "012345MATCH"
        matcher = ContentMatcher("MATCH")
        result = matcher.match(text)
        assert result[0].position == 6

    def test_positions_are_ascending(self):
        """Positions should be in ascending order."""
        matcher = ContentMatcher("a")
        text = "a b a c a d a"
        result = matcher.match(text)
        positions = [s.position for s in result]
        assert positions == sorted(positions)
