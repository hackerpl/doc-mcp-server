"""Data models and type definitions for FTP Doc Reader."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class FTPConfig:
    """FTP connection configuration."""

    host: str
    port: int
    username: str
    password: str
    protocol: Literal["FTP", "FTPS"]
    cache_dir: Path


@dataclass
class ScanResult:
    """Result of directory scanning operation."""

    files: list[str]  # discovered file paths
    truncated: bool  # True if file limit (200) was reached
    warnings: list[str]  # skipped directories, etc.


@dataclass
class MatchSnippet:
    """A single matched content snippet."""

    text: str  # snippet text with surrounding context
    position: int  # character position of match in original text


@dataclass
class SearchResult:
    """Search result for a single file."""

    file_path: str  # full remote path
    file_name: str  # file name only
    snippets: list[str]  # matched context snippets (max 5 per file)
