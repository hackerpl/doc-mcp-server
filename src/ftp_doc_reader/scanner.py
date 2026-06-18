"""Directory scanner for recursive FTP directory traversal."""

import logging
from pathlib import PurePosixPath

from ftp_doc_reader.ftp_client import FTPClient, FTPPermanentError
from ftp_doc_reader.models import ScanResult

logger = logging.getLogger(__name__)

# Maximum recursion depth for directory traversal
MAX_DEPTH = 10

# Maximum number of document files to collect
MAX_FILES = 200

# Supported document file extensions (lowercase)
SUPPORTED_EXTENSIONS = {".doc", ".docx"}


class DirectoryScanner:
    """Scans remote FTP directories recursively for .doc/.docx files."""

    def __init__(self, ftp_client: FTPClient):
        self._ftp_client = ftp_client

    async def scan(self, directory_path: str) -> ScanResult:
        """Recursively scan remote directory for .doc/.docx files.

        Returns ScanResult with list of remote file paths.
        Max depth: 10, max files: 200.

        Raises:
            FTPPermanentError: If the top-level directory does not exist.
        """
        files: list[str] = []
        warnings: list[str] = []
        truncated = False

        # Try listing the top-level directory; raise if not found
        try:
            entries = await self._ftp_client.list_directory(directory_path)
        except FTPPermanentError as exc:
            if exc.is_not_found:
                raise
            # Permission denied at top-level should also raise
            raise

        # Recursively scan starting at depth 0
        truncated = await self._scan_recursive(
            directory_path, entries, files, warnings, current_depth=0
        )

        return ScanResult(files=files, truncated=truncated, warnings=warnings)

    async def _scan_recursive(
        self,
        current_path: str,
        entries: list[tuple[str, str]],
        files: list[str],
        warnings: list[str],
        current_depth: int,
    ) -> bool:
        """Recursively process directory entries.

        Args:
            current_path: The current remote directory path being scanned.
            entries: List of (name, type) tuples from list_directory.
            files: Accumulator list of discovered file paths.
            warnings: Accumulator list of warning messages.
            current_depth: Current recursion depth (0-indexed).

        Returns:
            True if file limit was reached (truncated), False otherwise.
        """
        for name, entry_type in entries:
            # Check if file limit reached
            if len(files) >= MAX_FILES:
                return True

            # Build full path using POSIX-style separator for FTP
            full_path = f"{current_path.rstrip('/')}/{name}"

            if entry_type == "file":
                # Check extension (case-insensitive)
                suffix = PurePosixPath(name).suffix.lower()
                if suffix in SUPPORTED_EXTENSIONS:
                    files.append(full_path)
                    if len(files) >= MAX_FILES:
                        return True
            elif entry_type == "dir":
                # Stop recursing if max depth reached
                if current_depth >= MAX_DEPTH:
                    continue

                # Try to list subdirectory
                try:
                    sub_entries = await self._ftp_client.list_directory(full_path)
                except FTPPermanentError as exc:
                    if exc.is_permission_denied:
                        warning_msg = (
                            f"Skipped directory '{full_path}': permission denied"
                        )
                        warnings.append(warning_msg)
                        logger.warning(warning_msg)
                        continue
                    # Other permanent errors (e.g., not_found for subdirectory)
                    # are unexpected but we skip gracefully
                    warning_msg = f"Skipped directory '{full_path}': {exc}"
                    warnings.append(warning_msg)
                    logger.warning(warning_msg)
                    continue

                # Recurse into subdirectory
                truncated = await self._scan_recursive(
                    full_path, sub_entries, files, warnings, current_depth + 1
                )
                if truncated:
                    return True

        return False
