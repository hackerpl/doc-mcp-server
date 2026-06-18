# Implementation Plan: ftp-doc-reader-mcp

## Overview

本实现计划将 ftp-doc-reader-mcp 的设计分解为增量式编码任务。每个任务构建在前一个任务的基础上，最终将所有组件连接到 MCP 服务器的 `search_docs` 工具中。实现语言为 Python，使用 FastMCP SDK、python-docx、olefile 等库。

## Tasks

- [x] 1. 项目结构与基础设施搭建
  - [x] 1.1 创建项目目录结构和 pyproject.toml
    - 创建 `src/ftp_doc_reader/` 包目录结构
    - 编写 `pyproject.toml`，声明项目元数据、Python >= 3.10 要求、运行时依赖（mcp、python-dotenv、python-docx、olefile）、开发依赖（pytest、pytest-asyncio、pytest-mock、hypothesis、pytest-cov、pyftpdlib）
    - 定义控制台脚本入口点供 `uvx` 使用
    - 创建 `src/ftp_doc_reader/__init__.py`
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 1.2 创建数据模型和类型定义
    - 在 `src/ftp_doc_reader/models.py` 中定义 `FTPConfig`、`ScanResult`、`MatchSnippet`、`SearchResult` 数据类
    - `FTPConfig` 为 frozen dataclass，包含 host、port、username、password、protocol、cache_dir 字段
    - `ScanResult` 包含 files、truncated、warnings 字段
    - `SearchResult` 包含 file_path、file_name、snippets 字段
    - _Requirements: 1.1, 3.4_

- [x] 2. 配置加载与输入验证
  - [x] 2.1 实现配置加载模块 (`config.py`)
    - 使用 `python-dotenv` 从 `.env` 文件读取环境变量
    - 验证必填字段（host、username、password）存在且非空
    - 验证 port 在 1–65535 范围内，默认值 21
    - 验证 protocol 为 "FTP" 或 "FTPS"，默认值 "FTP"
    - cache_dir 默认值 ".cache"
    - 验证失败时终止启动并输出明确错误信息（指明每个无效字段）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 2.2 编写配置加载属性测试
    - **Property 7: Configuration validation**
    - **Validates: Requirements 5.3, 5.5, 5.6**

  - [x] 2.3 实现输入验证模块 (`validator.py`)
    - 实现 `validate_search_params(query, directory_path)` 函数
    - 校验 query 非空且长度 1–500 字符
    - 校验 directory_path 非空且长度 1–1024 字符
    - 验证失败时抛出 ValueError 并附带描述性消息
    - _Requirements: 1.1, 1.3, 1.4_

  - [ ]* 2.4 编写输入验证单元测试
    - 测试空 query、空 directory_path、超长输入、正常输入
    - _Requirements: 1.3, 1.4_

- [x] 3. FTP 客户端实现
  - [x] 3.1 实现 FTP 客户端模块 (`ftp_client.py`)
    - 实现 `FTPClient` 类，接受 `FTPConfig` 参数
    - 根据 protocol 字段使用 `ftplib.FTP` 或 `ftplib.FTP_TLS` 建立连接
    - FTPS 连接使用 TLS 1.2+
    - 每次连接/下载强制 30 秒超时
    - 实现 `list_directory(path)` 方法返回 `list[tuple[str, str]]`（名称, 类型）
    - 实现 `download(remote_path, local_path)` 方法带重试逻辑
    - 实现 `get_size(remote_path)` 方法返回 `int | None`
    - 重试逻辑：瞬态错误（超时、拒绝、重置）最多 3 次，间隔 2 秒
    - 不可重试错误（认证失败、文件未找到、权限拒绝）立即抛出异常
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 3.2 编写重试逻辑属性测试
    - **Property 9: Retry logic correctness**
    - **Validates: Requirements 8.1, 8.2**

  - [ ]* 3.3 编写 FTP 客户端单元测试
    - Mock ftplib，测试超时场景、TLS 握手失败、认证失败
    - _Requirements: 4.4, 4.5, 8.1, 8.2_

- [x] 4. Checkpoint - 基础组件验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. 目录扫描器实现
  - [x] 5.1 实现目录扫描模块 (`scanner.py`)
    - 实现 `DirectoryScanner` 类，依赖 `FTPClient`
    - 实现 `scan(directory_path)` 异步方法，递归遍历远程目录
    - 过滤仅保留 `.doc`/`.docx` 文件（大小写不敏感扩展名匹配）
    - 限制递归深度不超过 10 层
    - 限制文件总数不超过 200 个，超出时截断并设置 `truncated=True`
    - 无权限子目录跳过并记录 warnings
    - 目录不存在时返回明确错误
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 1.5_

  - [ ]* 5.2 编写目录扫描文件过滤属性测试
    - **Property 2: Directory scanner file filter**
    - **Validates: Requirements 2.1, 2.2**

  - [ ]* 5.3 编写目录扫描边界限制属性测试
    - **Property 3: Directory scanner bounds**
    - **Validates: Requirements 2.4, 2.5**

  - [ ]* 5.4 编写目录扫描单元测试
    - 测试空目录、权限拒绝目录、目录不存在场景
    - _Requirements: 2.3, 1.5, 1.6_

- [x] 6. 缓存管理器实现
  - [x] 6.1 实现缓存管理模块 (`cache.py`)
    - 实现 `CacheManager` 类，依赖 `cache_dir` 和 `FTPClient`
    - 实现 `get_file(remote_path)` 异步方法，返回本地文件 Path
    - 远程路径映射为本地缓存路径：保留目录层级、替换不安全字符（空格→`_`）
    - 通过 FTP SIZE 命令比较文件大小判断缓存有效性
    - 大小不一致或 SIZE 失败时重新下载
    - 缓存写入失败时记录警告并继续使用已下载文件
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 6.2 编写缓存路径映射属性测试
    - **Property 10: Cache path mapping determinism**
    - **Validates: Requirements 9.1**

  - [ ]* 6.3 编写缓存管理单元测试
    - 测试 SIZE 不一致重下载、SIZE 失败重下载、写入失败降级
    - _Requirements: 9.3, 9.4, 9.5, 9.6_

- [x] 7. 文本提取器实现
  - [x] 7.1 实现文本提取模块 (`extractor.py`)
    - 实现 `TextExtractor` 类，根据扩展名路由到子提取器
    - 实现 `DocxExtractor`：使用 `python-docx` 遍历段落和表格单元格，以 `\n` 连接
    - 实现 `DocExtractor`：使用 `olefile` 解析 OLE 容器，读取 WordDocument 流并解码文本
    - 处理损坏文件（返回错误消息并跳过）
    - 处理加密文件（返回错误消息并跳过）
    - .doc 文件超过 50 MB 时返回错误消息
    - 无文本内容时返回空字符串
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 7.2 编写 .docx 提取 round-trip 属性测试
    - **Property 8: .docx extraction round-trip**
    - **Validates: Requirements 6.1, 6.2**

  - [ ]* 7.3 编写文本提取单元测试
    - 测试损坏 .docx、加密 .doc、空文件、超大 .doc 文件
    - _Requirements: 6.3, 6.4, 6.5, 7.3, 7.4, 7.5_

- [x] 8. 内容匹配器实现
  - [x] 8.1 实现内容匹配模块 (`matcher.py`)
    - 实现 `ContentMatcher` 类，接受 query 参数
    - 实现 `match(text)` 方法：大小写不敏感的关键词搜索
    - 为每个匹配位置生成上下文片段（前后各 100 字符）
    - 每个文档最多返回 5 个匹配片段
    - 无匹配时返回空列表
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 8.2 编写内容匹配正确性属性测试
    - **Property 1: Content match correctness**
    - **Validates: Requirements 1.2, 1.7, 3.1**

  - [ ]* 8.3 编写大小写不敏感匹配属性测试
    - **Property 4: Case-insensitive matching equivalence**
    - **Validates: Requirements 3.1**

  - [ ]* 8.4 编写片段输出有效性属性测试
    - **Property 5: Snippet output validity**
    - **Validates: Requirements 3.2, 3.3**

- [x] 9. Checkpoint - 核心组件验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. 服务器集成与端到端连接
  - [x] 10.1 实现 MCP 服务器主模块 (`server.py`)
    - 使用 FastMCP 创建服务器实例
    - 注册 `search_docs` 工具（使用 `@mcp.tool()` 装饰器）
    - 启动时调用 `load_config()` 加载配置
    - 编排完整的请求处理流程：验证 → 目录扫描 → 缓存/下载 → 文本提取 → 内容匹配 → 结果排序
    - 按 snippets 数量降序排序结果
    - 处理各层级错误并返回结构化错误消息或结果列表
    - 无文档文件时返回空列表并附带提示信息
    - 有文档但无匹配时返回空列表
    - _Requirements: 1.1, 1.2, 1.5, 1.6, 1.7, 3.5_

  - [ ]* 10.2 编写结果排序属性测试
    - **Property 6: Results sorted by snippet count**
    - **Validates: Requirements 3.5**

  - [ ]* 10.3 编写集成测试
    - 使用 `pyftpdlib` 搭建本地 FTP 测试服务器
    - 端到端验证 search_docs 完整流程
    - 测试 FTP/FTPS 连接、目录扫描、下载、提取、匹配全链路
    - _Requirements: 1.2, 2.1, 3.1, 3.5_

- [x] 11. 部署配置与烟雾测试
  - [x] 11.1 完善部署配置和文档
    - 创建 `.env.example` 示例配置文件
    - 确保 `pyproject.toml` 入口点正确配置
    - 验证 `uvx` 可正常启动服务器
    - 添加 `__main__.py` 支持 `python -m` 启动
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ]* 11.2 编写烟雾测试
    - 验证 MCP 工具注册（工具名、参数 schema）
    - 验证 pyproject.toml 入口点和依赖声明
    - 验证服务器启动流程
    - _Requirements: 1.1, 10.2, 10.3_

- [x] 12. Final checkpoint - 全部测试通过
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- 标记 `*` 的任务为可选项，可跳过以加快 MVP 交付
- 每个任务引用了具体的需求条目以保证可追溯性
- Checkpoint 任务确保增量验证
- 属性测试验证设计文档中的通用正确性属性
- 单元测试验证具体场景和边界条件
- 集成测试使用本地 FTP 服务器验证端到端流程

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.3"] },
    { "id": 2, "tasks": ["2.2", "2.4", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3", "5.1", "6.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "5.4", "6.2", "6.3", "7.1"] },
    { "id": 5, "tasks": ["7.2", "7.3", "8.1"] },
    { "id": 6, "tasks": ["8.2", "8.3", "8.4"] },
    { "id": 7, "tasks": ["10.1"] },
    { "id": 8, "tasks": ["10.2", "10.3", "11.1"] },
    { "id": 9, "tasks": ["11.2"] }
  ]
}
```
