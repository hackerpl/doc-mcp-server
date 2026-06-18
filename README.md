# FTP Doc Reader MCP Server

[中文文档](README_CN.md)

An MCP (Model Context Protocol) server that recursively searches `.doc` and `.docx` files in a specified directory on a remote FTP/FTPS server, matches document content by keyword, and returns relevant files with context snippets.

## Features

- **Recursive directory scanning**: Automatically scans all Word documents in FTP directories and subdirectories (max depth 10, max 200 files)
- **Content keyword matching**: Case-insensitive full-text search, returns context snippets (100 characters before and after each match)
- **Supports .doc and .docx**: Handles both legacy binary format and modern XML format
- **FTP/FTPS dual protocol**: Supports plain FTP and TLS-encrypted FTPS
- **Local file caching**: Size-based cache invalidation strategy to avoid redundant downloads
- **Auto retry**: Transient network errors are automatically retried 3 times (2-second intervals)
- **Deploy via uvx**: No manual dependency management required

## Installation

### Via uvx (Recommended)

```bash
uvx ftp-doc-reader
```

### From source

```bash
git clone https://github.com/hackerpl/doc-mcp-server.git
cd doc-mcp-server
pip install -e .
```

## MCP Configuration

### Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ftp-doc-reader": {
      "command": "uvx",
      "args": ["ftp-doc-reader"],
      "env": {
        "FTP_HOST": "ftp.example.com",
        "FTP_USERNAME": "your_username",
        "FTP_PASSWORD": "your_password",
        "FTP_PROTOCOL": "FTP",
        "FTP_PORT": "21",
        "CACHE_DIR": ".cache"
      }
    }
  }
}
```

### Kiro

Edit `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "ftp-doc-reader": {
      "command": "uvx",
      "args": ["ftp-doc-reader"],
      "env": {
        "FTP_HOST": "ftp.example.com",
        "FTP_USERNAME": "your_username",
        "FTP_PASSWORD": "your_password"
      },
      "disabled": false,
      "autoApprove": ["search_docs"]
    }
  }
}
```

### Cursor

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ftp-doc-reader": {
      "command": "uvx",
      "args": ["ftp-doc-reader"],
      "env": {
        "FTP_HOST": "ftp.example.com",
        "FTP_USERNAME": "your_username",
        "FTP_PASSWORD": "your_password"
      }
    }
  }
}
```

### From GitHub source (development)

```json
{
  "mcpServers": {
    "ftp-doc-reader": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/hackerpl/doc-mcp-server.git", "ftp-doc-reader"],
      "env": {
        "FTP_HOST": "ftp.example.com",
        "FTP_USERNAME": "your_username",
        "FTP_PASSWORD": "your_password"
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FTP_HOST` | ✅ | — | FTP server hostname or IP |
| `FTP_USERNAME` | ✅ | — | FTP login username |
| `FTP_PASSWORD` | ✅ | — | FTP login password |
| `FTP_PORT` | ❌ | `21` | FTP server port |
| `FTP_PROTOCOL` | ❌ | `FTP` | Connection protocol: `FTP` or `FTPS` |
| `CACHE_DIR` | ❌ | `.cache` | Local cache directory path |

Environment variables can be set via the `env` field in MCP configuration, or by placing a `.env` file in the project directory.

## MCP Tool

### search_docs

Search Word document content in a remote FTP directory.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string (1-500 chars) | Search keyword or phrase |
| `directory_path` | string (1-1024 chars) | Remote FTP directory path |

**Returns:**

A list of matching results (sorted by match count descending), each containing:
- `file_path` — Full remote path of the file
- `file_name` — File name
- `snippets` — List of matched context snippets (max 5 per file)

**Usage example:**

```
Search for documents containing "installation guide" in the /products/docs directory on the FTP server
```

The AI assistant will call:
```json
{
  "tool": "search_docs",
  "arguments": {
    "query": "installation guide",
    "directory_path": "/products/docs"
  }
}
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov

# Start server directly (requires .env file)
python -m ftp_doc_reader
```

## Tech Stack

- Python 3.10+
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (FastMCP)
- python-docx (.docx parsing)
- olefile (.doc parsing)
- python-dotenv (environment variable management)

## License

MIT
