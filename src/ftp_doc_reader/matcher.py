"""Content matcher for case-insensitive keyword matching with context snippets."""

from .models import MatchSnippet


class ContentMatcher:
    """Performs case-insensitive keyword matching on text content.

    For each match found, generates a context snippet containing up to
    100 characters before and after the match position. Returns at most
    5 snippets per document.
    """

    # Maximum number of snippets to return per document
    MAX_SNIPPETS = 5
    # Number of context characters before and after match
    CONTEXT_SIZE = 100

    def __init__(self, query: str) -> None:
        """Initialize matcher with search query.

        Args:
            query: The keyword or phrase to search for.
        """
        self._query = query
        self._query_lower = query.lower()

    def match(self, text: str) -> list[MatchSnippet]:
        """Perform case-insensitive keyword matching on text.

        Searches for all occurrences of the query in the text (case-insensitive)
        and returns up to 5 context snippets with 100 chars before and after.

        Args:
            text: The text content to search in.

        Returns:
            A list of MatchSnippet instances (at most 5). Empty list if no match.
        """
        if not self._query or not text:
            return []

        text_lower = text.lower()
        query_len = len(self._query_lower)
        snippets: list[MatchSnippet] = []

        # Find all match positions using case-insensitive comparison
        start = 0
        while start <= len(text_lower) - query_len:
            pos = text_lower.find(self._query_lower, start)
            if pos == -1:
                break

            # Build context snippet
            snippet_text = self._build_snippet(text, pos, query_len)
            snippets.append(MatchSnippet(text=snippet_text, position=pos))

            # Stop after collecting MAX_SNIPPETS
            if len(snippets) >= self.MAX_SNIPPETS:
                break

            # Move past this match to find next
            start = pos + 1

        return snippets

    def _build_snippet(self, text: str, match_pos: int, match_len: int) -> str:
        """Build a context snippet around a match position.

        Extracts up to CONTEXT_SIZE characters before and after the match.
        Adds "..." prefix if there's text before the snippet start,
        and "..." suffix if there's text after the snippet end.

        Args:
            text: The full text content.
            match_pos: Character position where match starts.
            match_len: Length of the matched keyword.

        Returns:
            The snippet string with ellipsis indicators where applicable.
        """
        # Calculate snippet boundaries
        snippet_start = max(0, match_pos - self.CONTEXT_SIZE)
        snippet_end = min(len(text), match_pos + match_len + self.CONTEXT_SIZE)

        # Extract the raw snippet text
        snippet = text[snippet_start:snippet_end]

        # Add ellipsis indicators
        if snippet_start > 0:
            snippet = "..." + snippet
        if snippet_end < len(text):
            snippet = snippet + "..."

        return snippet
