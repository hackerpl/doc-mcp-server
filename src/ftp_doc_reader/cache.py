"""Cache manager for local file caching with size-based invalidation."""

import logging
import re
import tempfile
from pathlib import Path

from ftp_doc_reader.ftp_client import FTPClient

logger = logging.getLogger(__name__)

# Characters considered unsafe for file system paths (replaced with underscore)
_UNSAFE_CHARS_PATTERN = re.compile(r'[\s<>:"|?*]')


class CacheManager:
    """Manages local file cache with size-based invalidation.

    Downloads files from FTP server and caches them locally. Uses FTP SIZE
    command to determine if cached files are still valid by comparing file sizes.
    """

    def __init__(self, cache_dir: Path, ftp_client: FTPClient):
        """Initialize cache manager.

        Args:
            cache_dir: Local directory for cached files.
            ftp_client: FTP client instance for remote operations.
        """
        self._cache_dir = cache_dir
        self._ftp_client = ftp_client

    async def get_file(self, remote_path: str) -> Path:
        """Get local path to a file, downloading if cache is stale or missing.

        Checks cache validity by comparing local and remote file sizes.
        If sizes differ or SIZE command fails, re-downloads the file.

        Args:
            remote_path: Full path to file on the remote FTP server.

        Returns:
            Path to the local file (cached or freshly downloaded).

        Raises:
            FTPTransientError: After retries exhausted for download.
            FTPPermanentError: For non-retryable FTP errors during download.
        """
        local_path = self._local_path(remote_path)

        # Check if cached file exists
        if local_path.exists():
            # Compare sizes to determine cache validity
            remote_size = await self._ftp_client.get_size(remote_path)

            if remote_size is not None:
                local_size = local_path.stat().st_size
                if local_size == remote_size:
                    logger.debug(
                        "Cache hit for %s (size=%d)", remote_path, local_size
                    )
                    return local_path
                else:
                    logger.info(
                        "Cache stale for %s (local=%d, remote=%d), re-downloading",
                        remote_path,
                        local_size,
                        remote_size,
                    )
            else:
                # SIZE command failed - conservative strategy: re-download
                logger.info(
                    "SIZE command failed for %s, re-downloading", remote_path
                )
        else:
            logger.debug("Cache miss for %s, downloading", remote_path)

        # Download the file
        return await self._download_to_cache(remote_path, local_path)

    async def _download_to_cache(
        self, remote_path: str, local_path: Path
    ) -> Path:
        """Download file and attempt to store in cache.

        If cache write fails (disk full, permission error), logs a warning
        and returns a temporary file path instead.

        Args:
            remote_path: Remote file path on FTP server.
            local_path: Intended local cache path.

        Returns:
            Path to the downloaded file (cache path or temp file on write failure).
        """
        try:
            # Ensure cache directory structure exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            # Download directly to cache location
            await self._ftp_client.download(remote_path, local_path)
            logger.debug("Downloaded and cached: %s -> %s", remote_path, local_path)
            return local_path
        except OSError as exc:
            # Cache write failure (disk full, permission error, etc.)
            logger.warning(
                "Failed to write cache file %s: %s. Using temporary file.",
                local_path,
                exc,
            )
            # Fall back to temp file
            return await self._download_to_temp(remote_path)

    async def _download_to_temp(self, remote_path: str) -> Path:
        """Download file to a temporary location as fallback.

        Args:
            remote_path: Remote file path on FTP server.

        Returns:
            Path to the temporary downloaded file.
        """
        # Determine suffix from remote path for proper file handling
        suffix = Path(remote_path).suffix or ""
        tmp_fd = tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False, prefix="ftp_cache_"
        )
        tmp_path = Path(tmp_fd.name)
        tmp_fd.close()

        await self._ftp_client.download(remote_path, tmp_path)
        logger.debug("Downloaded to temp file: %s -> %s", remote_path, tmp_path)
        return tmp_path

    def _local_path(self, remote_path: str) -> Path:
        """Convert remote path to a path-safe local cache path.

        Preserves directory hierarchy from the remote path while replacing
        characters that are unsafe for file systems.

        Mapping rules:
        - Leading slashes are stripped
        - Spaces and other unsafe chars are replaced with underscore
        - Path separators are normalized to OS-native format

        Example:
            /reports/2024/Q1 summary.docx -> {cache_dir}/reports/2024/Q1_summary.docx

        Args:
            remote_path: Remote file path on FTP server.

        Returns:
            Local path within the cache directory.
        """
        # Strip leading slashes to make it a relative path
        clean_path = remote_path.lstrip("/")

        # Split into parts, sanitize each part, then rejoin
        parts = clean_path.replace("\\", "/").split("/")
        safe_parts = [_UNSAFE_CHARS_PATTERN.sub("_", part) for part in parts if part]

        # Join parts using OS-native path separator
        return self._cache_dir.joinpath(*safe_parts)
