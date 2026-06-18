"""FTP/FTPS client with retry logic and timeout handling."""

import asyncio
import ftplib
import logging
import socket
import ssl
from pathlib import Path

from ftp_doc_reader.models import FTPConfig

logger = logging.getLogger(__name__)

# Connection and operation timeout in seconds
TIMEOUT_SECONDS = 30

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


class FTPTransientError(Exception):
    """Raised for retryable FTP errors (timeout, connection refused, reset)."""

    pass


class FTPPermanentError(Exception):
    """Raised for non-retryable FTP errors (auth failure, not found, permission denied)."""

    def __init__(self, message: str, error_type: str = "unknown"):
        super().__init__(message)
        self.error_type = error_type

    @property
    def is_auth_failure(self) -> bool:
        return self.error_type == "auth_failure"

    @property
    def is_not_found(self) -> bool:
        return self.error_type == "not_found"

    @property
    def is_permission_denied(self) -> bool:
        return self.error_type == "permission_denied"


def _classify_error(exc: Exception) -> Exception:
    """Classify an FTP exception as transient or permanent.

    Returns:
        FTPTransientError for retryable errors.
        FTPPermanentError for non-retryable errors.
    """
    # Transient errors: timeout, connection refused, connection reset
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return FTPTransientError(f"Connection timed out: {exc}")

    if isinstance(exc, ConnectionRefusedError):
        return FTPTransientError(f"Connection refused: {exc}")

    if isinstance(exc, ConnectionResetError):
        return FTPTransientError(f"Connection reset: {exc}")

    if isinstance(exc, OSError) and "timed out" in str(exc).lower():
        return FTPTransientError(f"Operation timed out: {exc}")

    # Permanent errors from FTP response codes
    if isinstance(exc, ftplib.error_perm):
        response = str(exc)
        if response.startswith("530"):
            return FTPPermanentError(
                f"Authentication failed: {exc}", error_type="auth_failure"
            )
        if response.startswith("550"):
            return FTPPermanentError(
                f"File or directory not found: {exc}", error_type="not_found"
            )
        if response.startswith("553"):
            return FTPPermanentError(
                f"Permission denied: {exc}", error_type="permission_denied"
            )
        # Other permanent FTP errors
        return FTPPermanentError(f"FTP error: {exc}", error_type="unknown")

    # SSL/TLS errors are non-retryable
    if isinstance(exc, ssl.SSLError):
        return FTPPermanentError(
            f"TLS negotiation failed: {exc}", error_type="tls_failure"
        )

    # Default: treat unknown errors as transient to allow retry
    if isinstance(exc, (OSError, EOFError)):
        return FTPTransientError(f"Network error: {exc}")

    # Truly unknown errors - raise as permanent
    return FTPPermanentError(f"Unexpected error: {exc}", error_type="unknown")


class FTPClient:
    """FTP/FTPS client with automatic retry for transient errors."""

    def __init__(self, config: FTPConfig):
        self._config = config

    def _create_connection(self) -> ftplib.FTP:
        """Create and authenticate an FTP or FTPS connection.

        Returns:
            Connected and authenticated FTP instance.

        Raises:
            FTPTransientError: For retryable connection errors.
            FTPPermanentError: For non-retryable errors (auth, TLS failure).
        """
        try:
            if self._config.protocol == "FTPS":
                # Create SSL context with TLS 1.2+ enforcement
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                # Allow self-signed certificates in corporate environments
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                ftp = ftplib.FTP_TLS(
                    timeout=TIMEOUT_SECONDS,
                    context=ssl_context,
                    encoding="gbk",
                )
                ftp.connect(host=self._config.host, port=self._config.port)
                ftp.login(user=self._config.username, passwd=self._config.password)
                # Secure data connection
                ftp.prot_p()
            elif self._config.protocol == "FTP":
                ftp = ftplib.FTP(timeout=TIMEOUT_SECONDS, encoding="gbk")
                ftp.connect(host=self._config.host, port=self._config.port)
                ftp.login(user=self._config.username, passwd=self._config.password)
            else:
                raise FTPPermanentError(
                    f"Unsupported protocol: {self._config.protocol}",
                    error_type="invalid_protocol",
                )

            return ftp
        except (FTPTransientError, FTPPermanentError):
            raise
        except Exception as exc:
            raise _classify_error(exc) from exc

    async def _retry_operation(self, operation_name: str, func):
        """Execute a blocking FTP operation with retry logic.

        Retries up to MAX_RETRIES times for transient errors with
        RETRY_DELAY_SECONDS delay between attempts.

        Args:
            operation_name: Description for logging.
            func: Callable that performs the blocking FTP operation.

        Returns:
            Result of the operation.

        Raises:
            FTPTransientError: If all retry attempts are exhausted.
            FTPPermanentError: Immediately on non-retryable errors.
        """
        last_error: FTPTransientError | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = await asyncio.to_thread(func)
                return result
            except FTPPermanentError:
                # Non-retryable: propagate immediately
                raise
            except FTPTransientError as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %ds...",
                        operation_name,
                        attempt,
                        MAX_RETRIES,
                        exc,
                        RETRY_DELAY_SECONDS,
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(
                        "%s failed after %d attempts: %s",
                        operation_name,
                        MAX_RETRIES,
                        exc,
                    )
            except Exception as exc:
                # Classify unknown exceptions
                classified = _classify_error(exc)
                if isinstance(classified, FTPPermanentError):
                    raise classified from exc
                # Transient
                last_error = classified  # type: ignore[assignment]
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %ds...",
                        operation_name,
                        attempt,
                        MAX_RETRIES,
                        classified,
                        RETRY_DELAY_SECONDS,
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(
                        "%s failed after %d attempts: %s",
                        operation_name,
                        MAX_RETRIES,
                        classified,
                    )

        # All retries exhausted
        raise last_error  # type: ignore[misc]

    async def list_directory(self, path: str) -> list[tuple[str, str]]:
        """List directory contents on the remote FTP server.

        Args:
            path: Remote directory path to list.

        Returns:
            List of (name, type) tuples where type is 'file' or 'dir'.

        Raises:
            FTPTransientError: After retries exhausted for transient errors.
            FTPPermanentError: Immediately for auth/permission/not-found errors.
        """

        def _do_list() -> list[tuple[str, str]]:
            ftp = self._create_connection()
            try:
                entries: list[tuple[str, str]] = []
                lines: list[str] = []
                ftp.retrlines(f"MLSD {path}", lines.append)

                for line in lines:
                    # MLSD format: "facts; filename"
                    # e.g. "type=file;size=1234; filename.txt"
                    if ";" not in line:
                        continue
                    facts_part, _, name = line.rpartition("; ")
                    if not name or name in (".", ".."):
                        continue

                    # Parse entry type from facts
                    entry_type = "file"
                    for fact in facts_part.split(";"):
                        fact = fact.strip()
                        if fact.lower().startswith("type="):
                            type_value = fact.split("=", 1)[1].strip().lower()
                            if type_value in ("dir", "cdir", "pdir"):
                                entry_type = "dir"
                            else:
                                entry_type = "file"
                            break

                    entries.append((name, entry_type))
                return entries
            finally:
                try:
                    ftp.quit()
                except Exception:
                    ftp.close()

        return await self._retry_operation(f"list_directory({path})", _do_list)

    async def download(self, remote_path: str, local_path: Path) -> None:
        """Download a file from the remote FTP server with retry logic.

        Downloads up to MAX_RETRIES attempts with RETRY_DELAY_SECONDS delay.

        Args:
            remote_path: Path to file on the remote FTP server.
            local_path: Local destination path to save the file.

        Raises:
            FTPTransientError: After retries exhausted for transient errors.
            FTPPermanentError: Immediately for auth/permission/not-found errors.
        """

        def _do_download() -> None:
            ftp = self._create_connection()
            try:
                # Ensure parent directory exists
                local_path.parent.mkdir(parents=True, exist_ok=True)

                with open(local_path, "wb") as f:
                    ftp.retrbinary(f"RETR {remote_path}", f.write)
            except Exception:
                # Clean up partial file on failure
                if local_path.exists():
                    try:
                        local_path.unlink()
                    except OSError:
                        pass
                raise
            finally:
                try:
                    ftp.quit()
                except Exception:
                    ftp.close()

        await self._retry_operation(f"download({remote_path})", _do_download)

    async def get_size(self, remote_path: str) -> int | None:
        """Get the size of a remote file via the FTP SIZE command.

        Args:
            remote_path: Path to file on the remote FTP server.

        Returns:
            File size in bytes, or None if the SIZE command fails.
        """

        def _do_get_size() -> int | None:
            ftp = self._create_connection()
            try:
                ftp.voidcmd("TYPE I")  # Switch to binary mode for SIZE
                size = ftp.size(remote_path)
                return size
            except Exception:
                # SIZE command failure -> return None
                return None
            finally:
                try:
                    ftp.quit()
                except Exception:
                    ftp.close()

        try:
            return await asyncio.to_thread(_do_get_size)
        except Exception:
            # Any error in getting size -> return None
            return None
