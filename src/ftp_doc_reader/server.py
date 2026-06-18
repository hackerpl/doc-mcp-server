"""MCP server entry point with search_docs tool registration."""

import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ftp_doc_reader.cache import CacheManager
from ftp_doc_reader.config import load_config
from ftp_doc_reader.extractor import TextExtractor
from ftp_doc_reader.ftp_client import FTPClient, FTPPermanentError, FTPTransientError
from ftp_doc_reader.matcher import ContentMatcher
from ftp_doc_reader.models import FTPConfig, SearchResult
from ftp_doc_reader.scanner import DirectoryScanner
from ftp_doc_reader.validator import validate_search_params

logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("ftp-doc-reader")

# Error message prefix for extraction failures
_EXTRACTION_ERROR_PREFIX = "Error: Extraction - "


@mcp.tool()
async def search_docs(query: str, directory_path: str) -> list[dict] | str:
    """Search .doc/.docx files in a remote FTP directory for content matching the query.

    Args:
        query: Search keyword or phrase for content matching (1-500 characters).
        directory_path: Remote FTP directory path to search in (1-1024 characters).

    Returns:
        List of search results sorted by snippet count (descending),
        or an error message string on failure.
    """
    # Step 1: Input validation
    try:
        validate_search_params(query, directory_path)
    except ValueError as e:
        return str(e)

    # Step 2: Load configuration
    try:
        config = load_config()
    except SystemExit:
        return "Error: 服务器配置无效，请检查 .env 文件"

    # Step 3: Initialize components
    ftp_client = FTPClient(config)
    scanner = DirectoryScanner(ftp_client)
    cache_manager = CacheManager(config.cache_dir, ftp_client)
    text_extractor = TextExtractor()
    content_matcher = ContentMatcher(query)

    # Step 4: Scan directory for document files
    try:
        scan_result = await scanner.scan(directory_path)
    except FTPPermanentError as e:
        if e.is_not_found:
            return f"Error: 目录未找到: {directory_path}"
        if e.is_auth_failure:
            return f"Error: FTP 认证失败: {e}"
        return f"Error: FTP 操作失败: {e}"
    except FTPTransientError as e:
        return f"Error: FTP 连接失败（已重试 3 次）: {e}"

    # Step 5: Check if any document files were found
    if not scan_result.files:
        return "该目录下未找到支持的文档文件（.doc/.docx）"

    # Step 6: Process each file: cache/download -> extract -> match
    results: list[SearchResult] = []

    for remote_path in scan_result.files:
        try:
            # Download or use cached file
            local_path = await cache_manager.get_file(remote_path)

            # Extract text content
            text = text_extractor.extract(local_path)

            # Skip files with extraction errors
            if text.startswith(_EXTRACTION_ERROR_PREFIX):
                logger.warning(
                    "Skipping file %s: %s", remote_path, text
                )
                continue

            # Skip empty documents
            if not text:
                continue

            # Match content against query
            snippets = content_matcher.match(text)

            # Only include files with matches
            if snippets:
                file_name = Path(remote_path).name
                results.append(
                    SearchResult(
                        file_path=remote_path,
                        file_name=file_name,
                        snippets=[s.text for s in snippets],
                    )
                )
        except (FTPPermanentError, FTPTransientError) as e:
            logger.warning("Failed to process file %s: %s", remote_path, e)
            continue
        except Exception as e:
            logger.warning(
                "Unexpected error processing file %s: %s", remote_path, e
            )
            continue

    # Step 7: Sort results by snippet count (descending)
    results.sort(key=lambda r: len(r.snippets), reverse=True)

    # Step 8: Build response
    response: list[dict] = [
        {
            "file_path": r.file_path,
            "file_name": r.file_name,
            "snippets": r.snippets,
        }
        for r in results
    ]

    # Add truncation notice if applicable
    if scan_result.truncated:
        logger.info(
            "Search results may be incomplete: file count exceeded limit (200)"
        )

    return response


def main() -> None:
    """Entry point for the ftp-doc-reader MCP server.

    Called by the console script defined in pyproject.toml.
    Starts the MCP server using stdio transport.
    """
    mcp.run()
