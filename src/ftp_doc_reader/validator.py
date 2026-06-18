"""Input validation for search_docs tool parameters."""

# Maximum allowed length for query parameter
MAX_QUERY_LENGTH = 500

# Maximum allowed length for directory_path parameter
MAX_DIRECTORY_PATH_LENGTH = 1024


def validate_search_params(query: str, directory_path: str) -> None:
    """Validate search_docs input parameters.

    Args:
        query: Search keyword or phrase (1-500 characters).
        directory_path: Remote FTP directory path (1-1024 characters).

    Raises:
        ValueError: If any parameter is invalid.
    """
    # Validate query is not empty or missing
    if not query or not query.strip():
        raise ValueError("搜索关键词为必填项")

    # Validate query length does not exceed maximum
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError("查询长度超出限制（最大 500 字符）")

    # Validate directory_path is not empty or missing
    if not directory_path or not directory_path.strip():
        raise ValueError("目录路径为必填项")

    # Validate directory_path length does not exceed maximum
    if len(directory_path) > MAX_DIRECTORY_PATH_LENGTH:
        raise ValueError("路径长度超出限制（最大 1024 字符）")
