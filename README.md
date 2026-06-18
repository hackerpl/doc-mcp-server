# FTP Doc Reader MCP Server

一个基于 MCP（Model Context Protocol）的服务器，用于在远程 FTP/FTPS 服务器的指定目录中递归搜索 `.doc` 和 `.docx` 文件，并根据关键词匹配文档内容，返回相关文件和上下文片段。

## 功能特性

- **目录递归搜索**：自动扫描 FTP 目录及子目录下的所有 Word 文档（最深 10 层，最多 200 个文件）
- **内容关键词匹配**：大小写不敏感的全文搜索，返回匹配上下文片段（前后各 100 字符）
- **支持 .doc 和 .docx**：同时处理旧版二进制格式和现代 XML 格式
- **FTP/FTPS 双协议**：支持明文 FTP 和 TLS 加密的 FTPS
- **本地文件缓存**：基于文件大小的缓存失效策略，避免重复下载
- **自动重试**：瞬态网络错误自动重试 3 次（间隔 2 秒）
- **通过 uvx 部署**：无需手动管理依赖

## 安装

### 通过 uvx（推荐）

```bash
uvx ftp-doc-reader
```

### 从源码安装

```bash
git clone https://github.com/your-username/doc-mcp-server.git
cd doc-mcp-server
pip install -e .
```

## MCP 配置

### Claude Desktop

编辑 `claude_desktop_config.json`：

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

编辑 `.kiro/settings/mcp.json`：

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

编辑 `~/.cursor/mcp.json`：

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

### 本地开发（使用源码路径）

```json
{
  "mcpServers": {
    "ftp-doc-reader": {
      "command": "uvx",
      "args": ["--from", "/path/to/doc-mcp-server", "ftp-doc-reader"],
      "env": {
        "FTP_HOST": "ftp.example.com",
        "FTP_USERNAME": "your_username",
        "FTP_PASSWORD": "your_password"
      }
    }
  }
}
```

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `FTP_HOST` | ✅ | — | FTP 服务器主机名或 IP |
| `FTP_USERNAME` | ✅ | — | FTP 登录用户名 |
| `FTP_PASSWORD` | ✅ | — | FTP 登录密码 |
| `FTP_PORT` | ❌ | `21` | FTP 服务器端口 |
| `FTP_PROTOCOL` | ❌ | `FTP` | 连接协议：`FTP` 或 `FTPS` |
| `CACHE_DIR` | ❌ | `.cache` | 本地缓存目录路径 |

环境变量可通过 MCP 配置的 `env` 字段设置，也可在项目目录放一个 `.env` 文件。

## MCP 工具

### search_docs

在远程 FTP 目录中搜索 Word 文档内容。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | string (1-500字符) | 搜索关键词或短语 |
| `directory_path` | string (1-1024字符) | 远程 FTP 目录路径 |

**返回：**

匹配结果列表（按匹配数量降序排列），每项包含：
- `file_path` — 文件远程完整路径
- `file_name` — 文件名
- `snippets` — 匹配的上下文片段列表（每文件最多 5 个）

**使用示例：**

```
搜索 FTP 服务器 /products/docs 目录下包含"安装指南"的文档
```

AI 助手会调用：
```json
{
  "tool": "search_docs",
  "arguments": {
    "query": "安装指南",
    "directory_path": "/products/docs"
  }
}
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行测试（带覆盖率）
pytest --cov

# 直接启动服务器（需要 .env 文件）
python -m ftp_doc_reader
```

## 技术栈

- Python 3.10+
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (FastMCP)
- python-docx（.docx 解析）
- olefile（.doc 解析）
- python-dotenv（环境变量管理）

## 许可证

MIT
