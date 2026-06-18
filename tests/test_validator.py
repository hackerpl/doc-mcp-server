"""Unit tests for input validation module."""

import pytest

from ftp_doc_reader.validator import validate_search_params


class TestValidateSearchParams:
    """Tests for validate_search_params function."""

    # --- query validation ---

    def test_empty_query_raises_value_error(self):
        """Empty query string should raise ValueError."""
        with pytest.raises(ValueError, match="搜索关键词为必填项"):
            validate_search_params("", "/docs")

    def test_whitespace_only_query_raises_value_error(self):
        """Whitespace-only query should raise ValueError."""
        with pytest.raises(ValueError, match="搜索关键词为必填项"):
            validate_search_params("   ", "/docs")

    def test_query_exceeds_max_length_raises_value_error(self):
        """Query exceeding 500 characters should raise ValueError."""
        long_query = "a" * 501
        with pytest.raises(ValueError, match="查询长度超出限制"):
            validate_search_params(long_query, "/docs")

    def test_query_at_max_length_passes(self):
        """Query at exactly 500 characters should pass validation."""
        query = "a" * 500
        validate_search_params(query, "/docs")  # Should not raise

    # --- directory_path validation ---

    def test_empty_directory_path_raises_value_error(self):
        """Empty directory_path should raise ValueError."""
        with pytest.raises(ValueError, match="目录路径为必填项"):
            validate_search_params("keyword", "")

    def test_whitespace_only_directory_path_raises_value_error(self):
        """Whitespace-only directory_path should raise ValueError."""
        with pytest.raises(ValueError, match="目录路径为必填项"):
            validate_search_params("keyword", "   ")

    def test_directory_path_exceeds_max_length_raises_value_error(self):
        """directory_path exceeding 1024 characters should raise ValueError."""
        long_path = "/" + "a" * 1024
        with pytest.raises(ValueError, match="路径长度超出限制"):
            validate_search_params("keyword", long_path)

    def test_directory_path_at_max_length_passes(self):
        """directory_path at exactly 1024 characters should pass validation."""
        path = "/" + "a" * 1023
        validate_search_params("keyword", path)  # Should not raise

    # --- valid inputs ---

    def test_valid_inputs_pass(self):
        """Valid query and directory_path should not raise."""
        validate_search_params("安装指南", "/products/docs")

    def test_single_char_query_passes(self):
        """Single character query should pass validation."""
        validate_search_params("a", "/docs")

    def test_single_char_directory_path_passes(self):
        """Single character directory_path should pass validation."""
        validate_search_params("keyword", "/")
