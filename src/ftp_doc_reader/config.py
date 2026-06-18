"""Configuration loader for FTP connection parameters from .env file."""

import os
import sys
from pathlib import Path

from dotenv import dotenv_values

from ftp_doc_reader.models import FTPConfig


def load_config(env_path: Path | None = None) -> FTPConfig:
    """Load and validate configuration from .env file.

    Args:
        env_path: Optional path to .env file. If None, looks for .env in current directory.

    Returns:
        FTPConfig instance with validated configuration.

    Raises:
        SystemExit: If configuration is invalid (missing .env, missing required fields,
                    invalid port or protocol).
    """
    if env_path is None:
        env_path = Path(".env")

    # Load from .env file if available, otherwise fall back to os.environ
    if env_path.is_file():
        values = dotenv_values(env_path)
    else:
        keys = [
            "FTP_HOST", "FTP_PORT", "FTP_USERNAME", "FTP_PASSWORD",
            "FTP_PROTOCOL", "CACHE_DIR",
        ]
        values = {k: os.environ[k] for k in keys if k in os.environ}
        if not values:
            print(
                f"Error: Configuration file not found: {env_path} "
                f"and no FTP environment variables set",
                file=sys.stderr,
            )
            sys.exit(1)

    # Validate required fields
    required_fields = ["FTP_HOST", "FTP_USERNAME", "FTP_PASSWORD"]
    missing_fields = [
        field for field in required_fields if not values.get(field, "").strip()
    ]

    if missing_fields:
        field_names = ", ".join(missing_fields)
        print(
            f"Error: Missing required configuration: {field_names}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate port
    port_str = values.get("FTP_PORT", "").strip()
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            print(
                f"Error: Invalid port value: '{port_str}' is not a valid integer",
                file=sys.stderr,
            )
            sys.exit(1)

        if port < 1 or port > 65535:
            print(
                f"Error: Invalid port value: {port} is not in range 1-65535",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        port = 21

    # Validate protocol
    protocol_str = values.get("FTP_PROTOCOL", "").strip()
    if protocol_str:
        protocol_upper = protocol_str.upper()
        if protocol_upper not in ("FTP", "FTPS"):
            print(
                f"Error: Invalid protocol value: '{protocol_str}' "
                f"(must be 'FTP' or 'FTPS')",
                file=sys.stderr,
            )
            sys.exit(1)
        protocol = protocol_upper
    else:
        protocol = "FTP"

    # Apply default for cache_dir
    cache_dir_str = values.get("CACHE_DIR", "").strip()
    cache_dir = Path(cache_dir_str) if cache_dir_str else Path(".cache")

    return FTPConfig(
        host=values["FTP_HOST"].strip(),
        port=port,
        username=values["FTP_USERNAME"].strip(),
        password=values["FTP_PASSWORD"].strip(),
        protocol=protocol,  # type: ignore[arg-type]
        cache_dir=cache_dir,
    )
