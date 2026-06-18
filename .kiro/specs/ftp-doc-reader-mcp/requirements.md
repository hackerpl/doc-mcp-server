# Requirements Document

## Introduction

本文档定义了 **ftp-doc-reader-mcp** 的需求规格。该项目是一个基于 Python 的 MCP（Model Context Protocol）服务器，用于在远程 FTP 服务器上的指定目录中搜索 `.doc` 和 `.docx` 文件，提取文本内容并根据用户提供的查询关键词进行内容匹配，最终返回匹配的文件路径及相关内容片段。

核心使用场景：公司的产品文档存储在 FTP 服务器的某个文件夹中，用户不确定需要获取哪个产品的文档，因此需要通过关键词搜索该文件夹下所有文件的内容，找到与需求匹配的文档及其相关内容。

该服务器支持 FTP 和 FTPS 协议，使用环境变量（`.env`）进行配置，实现本地文件缓存与基于文件大小的缓存失效策略，对 FTP 失败操作进行重试，并可通过 `uvx` 部署。

## Glossary

- **MCP_Server**: 基于 Python 的 Model Context Protocol 服务器应用，托管并暴露工具供 AI 模型交互。
- **FTP_Client**: 负责与远程 FTP/FTPS 服务器建立连接、列出目录内容和传输文件的内部组件。
- **Text_Extractor**: 负责解析 `.doc` 和 `.docx` 文件并提取原始文本内容的组件。
- **Content_Matcher**: 负责将提取的文本内容与用户查询进行匹配，并返回相关内容片段的组件。
- **Directory_Scanner**: 负责遍历远程 FTP 目录（包括子目录）并列出所有符合条件的文档文件的组件。
- **Cache_Manager**: 负责在本地存储已下载文件并判断缓存文件是否仍然有效的组件。
- **Configuration_Loader**: 负责从 `.env` 文件读取 FTP 连接参数的组件。
- **FTP_Server**: 存储 `.doc` 和 `.docx` 文件的远程 FTP 或 FTPS 服务器。
- **Search_Query**: 用户提供的用于内容匹配的关键词或短语字符串。
- **Directory_Path**: 表示远程 FTP 服务器上要搜索的目录路径的字符串。
- **Search_Result**: 包含匹配文件路径和相关内容片段的结构化结果。
- **Cache_Directory**: 存储已下载 FTP 文件用于缓存的本地目录。

## Requirements

### Requirement 1: MCP 工具暴露

**User Story:** 作为 AI 模型使用者，我希望调用一个 MCP 工具，传入搜索关键词和 FTP 目录路径，从而在该目录下的所有 Word 文档中搜索匹配的内容。

#### Acceptance Criteria

1. THE MCP_Server SHALL 暴露一个名为 `search_docs` 的工具，该工具接受两个参数：`query`（类型为字符串，1 到 500 个字符的 Search_Query）和 `directory_path`（类型为字符串，1 到 1024 个字符的 Directory_Path），并返回 Search_Result 列表。
2. WHEN `search_docs` 工具被调用且 `directory_path` 指定的远程目录中包含 `.doc` 或 `.docx` 文件，THE MCP_Server SHALL 提取每个文件的文本内容，将其与 `query` 进行匹配，并返回所有包含匹配内容的 Search_Result 列表。
3. IF `search_docs` 工具被调用时 `query` 参数为空或缺失，THEN THE MCP_Server SHALL 返回错误消息，指明搜索关键词为必填项。
4. IF `search_docs` 工具被调用时 `directory_path` 参数为空或缺失，THEN THE MCP_Server SHALL 返回错误消息，指明目录路径为必填项。
5. IF 指定的 `directory_path` 在远程 FTP_Server 上不存在，THEN THE MCP_Server SHALL 返回错误消息，指明目录未找到。
6. WHEN 指定目录中没有任何 `.doc` 或 `.docx` 文件，THE MCP_Server SHALL 返回空的 Search_Result 列表，并附带提示信息说明该目录下未找到支持的文档文件。
7. WHEN 指定目录中有文档文件但没有任何文件内容与 `query` 匹配，THE MCP_Server SHALL 返回空的 Search_Result 列表。

### Requirement 2: 目录扫描与文件发现

**User Story:** 作为 AI 模型使用者，我希望工具能自动扫描 FTP 目录（包括子目录）下的所有 Word 文档，以便我不需要知道具体文件路径。

#### Acceptance Criteria

1. WHEN `search_docs` 工具被调用，THE Directory_Scanner SHALL 递归遍历 `directory_path` 指定的远程目录及其所有子目录，列出所有以 `.doc` 或 `.docx` 结尾（大小写不敏感）的文件。
2. THE Directory_Scanner SHALL 跳过扩展名不是 `.doc` 或 `.docx` 的文件，不对其进行下载或处理。
3. IF 递归扫描过程中遇到无法访问的子目录（权限不足），THEN THE Directory_Scanner SHALL 跳过该子目录并记录警告日志，继续扫描其余目录。
4. IF 递归扫描的目录层级超过 10 层，THEN THE Directory_Scanner SHALL 停止继续深入扫描，仅处理已发现的文件。
5. IF 目录中发现的文档文件总数超过 200 个，THEN THE Directory_Scanner SHALL 仅处理前 200 个文件，并在结果中附带提示信息说明文件数量超出限制。

### Requirement 3: 内容搜索与匹配

**User Story:** 作为 AI 模型使用者，我希望工具能根据我提供的关键词在文档内容中进行匹配，返回包含关键词的文件及相关内容片段，以便我快速定位所需文档。

#### Acceptance Criteria

1. WHEN 文档文本已被提取，THE Content_Matcher SHALL 对文本内容进行大小写不敏感的关键词匹配，判断文本中是否包含 `query` 指定的关键词或短语。
2. WHEN 文档内容包含匹配的关键词，THE Content_Matcher SHALL 返回包含该关键词的上下文片段，每个片段包含匹配位置前后各 100 个字符的文本内容。
3. WHEN 一个文档中存在多个匹配位置，THE Content_Matcher SHALL 返回最多 5 个匹配片段。
4. THE Search_Result SHALL 包含以下字段：文件的远程完整路径（`file_path`）、匹配片段列表（`snippets`）、以及文件名（`file_name`）。
5. THE MCP_Server SHALL 按照匹配片段数量从多到少的顺序对 Search_Result 列表进行排序后返回。

### Requirement 4: FTP 和 FTPS 协议支持

**User Story:** 作为系统管理员，我希望服务器同时支持 FTP 和 FTPS 协议，以便连接到有或没有 TLS 加密的服务器。

#### Acceptance Criteria

1. WHEN 配置指定 FTP 协议，THE FTP_Client SHALL 在配置的端口上与 FTP_Server 建立未加密的连接，超时时间为 30 秒。
2. WHEN 配置指定 FTPS 协议，THE FTP_Client SHALL 在配置的端口上与 FTP_Server 建立 TLS 加密连接，超时时间为 30 秒。
3. WHEN 配置指定 FTPS 协议，THE FTP_Client SHALL 使用 TLS 1.2 或更高版本进行加密连接。
4. IF FTP_Client 在 30 秒内无法与 FTP_Server 建立连接，THEN THE FTP_Client SHALL 报告错误消息，指明连接超时及目标主机。
5. IF 配置指定 FTPS 且 TLS 握手失败，THEN THE FTP_Client SHALL 报告错误消息指明 TLS 协商失败，且不得回退到未加密连接。
6. IF 配置指定了不受支持的协议值（既不是 FTP 也不是 FTPS），THEN THE FTP_Client SHALL 报告错误消息，指明协议配置无效。

### Requirement 5: 环境变量配置

**User Story:** 作为部署服务器的开发者，我希望通过 `.env` 文件配置 FTP 连接参数，以便在不修改源代码的情况下管理凭据和设置。

#### Acceptance Criteria

1. THE Configuration_Loader SHALL 从 `.env` 文件中读取以下参数：host、port、username、password、protocol（FTP 或 FTPS）以及 cache directory path。
2. WHEN `.env` 文件缺失，THE Configuration_Loader SHALL 终止启动并记录错误日志，指明缺少的文件。
3. WHEN 必需参数（host、username、password）在 `.env` 文件中缺失，THE Configuration_Loader SHALL 终止启动并记录错误日志，指明每个缺失的参数名称。
4. IF port 参数未指定，THEN THE Configuration_Loader SHALL 使用 21 作为默认值。IF protocol 参数未指定，THEN THE Configuration_Loader SHALL 使用 FTP 作为默认值。
5. IF port 参数值不是 1 到 65535 范围内的整数，THEN THE Configuration_Loader SHALL 终止启动并记录错误日志，指明端口值无效。
6. IF protocol 参数值不是允许的值之一（FTP、FTPS），THEN THE Configuration_Loader SHALL 终止启动并记录错误日志，指明协议值无效。

### Requirement 6: 文档文本提取 — .docx 格式

**User Story:** 作为 AI 模型使用者，我希望能从现代 `.docx` 文件中提取文本，以便获取基于 XML 的 Word 文档内容。

#### Acceptance Criteria

1. WHEN 提供 `.docx` 文件，THE Text_Extractor SHALL 解析 XML 结构并返回文档正文中的所有段落文本内容，以换行符（`\n`）分隔各段落，不包含页眉、页脚和文本框内容。
2. WHEN `.docx` 文件包含表格，THE Text_Extractor SHALL 提取每个单元格的文本并包含在输出中，单元格文本以换行符（`\n`）分隔。
3. WHEN `.docx` 文件不包含文本内容，THE Text_Extractor SHALL 返回空字符串。
4. IF `.docx` 文件已损坏或不是有效的 ZIP 压缩文件，THEN THE Text_Extractor SHALL 返回错误消息，指明该文件不是有效的 `.docx` 文档。
5. IF `.docx` 文件受密码保护或已加密，THEN THE Text_Extractor SHALL 返回错误消息，指明由于加密无法读取该文件。

### Requirement 7: 文档文本提取 — .doc 格式

**User Story:** 作为 AI 模型使用者，我希望能从旧版 `.doc` 文件中提取文本，以便获取二进制 Word 文档内容。

#### Acceptance Criteria

1. WHEN 提供有效的 `.doc` 文件，THE Text_Extractor SHALL 解析二进制 OLE 格式并返回所有文本内容，编码为 UTF-8 字符串，段落以换行符分隔。
2. WHEN `.doc` 文件不包含文本内容，THE Text_Extractor SHALL 返回空字符串。
3. IF 提供的 `.doc` 文件已损坏或不是有效的二进制 Word 文档，THEN THE Text_Extractor SHALL 返回错误消息，指明该文件不是有效的 `.doc` 文档，且不修改任何先前状态。
4. IF 提供的 `.doc` 文件大小超过 50 MB，THEN THE Text_Extractor SHALL 返回错误消息，指明文件超出支持的最大大小。
5. IF 提供的 `.doc` 文件受密码保护或已加密，THEN THE Text_Extractor SHALL 返回错误消息，指明文件受保护无法提取。

### Requirement 8: 重试逻辑

**User Story:** 作为系统运维人员，我希望服务器对失败的 FTP 操作进行重试，以便瞬态网络错误不会立即导致整体失败。

#### Acceptance Criteria

1. WHEN FTP 下载或目录列表操作因瞬态错误（连接超时、连接被拒绝或连接被重置）失败，THE FTP_Client SHALL 以 2 秒间隔重试该操作最多 3 次，然后再报告失败。
2. IF FTP 操作因不可重试的错误（认证失败、文件未找到或权限被拒绝）失败，THEN THE MCP_Server SHALL 返回错误消息，指明失败原因，不进行重试。
3. WHEN 瞬态错误的 3 次重试全部失败，THE MCP_Server SHALL 返回错误消息，指明失败原因及尝试次数。
4. WHEN 某次重试成功，THE MCP_Server SHALL 正常返回结果，不附带任何错误指示。
5. THE FTP_Client SHALL 对每次 FTP 连接或下载尝试强制执行 30 秒超时。

### Requirement 9: 本地文件缓存

**User Story:** 作为 AI 模型使用者，我希望已下载的文档在本地缓存，以便对同一目录的重复搜索能更快地返回结果而无需冗余下载。

#### Acceptance Criteria

1. WHEN 文档从 FTP_Server 成功下载，THE Cache_Manager SHALL 将文件存储在 Cache_Directory 中，使用路径安全的命名方案保留远程目录结构以避免文件名冲突。
2. WHEN 请求的文件已有缓存副本存在，THE Cache_Manager SHALL 发出 FTP SIZE 命令获取远程文件大小，并与本地缓存文件大小进行比较。
3. WHEN 远程文件大小与缓存文件大小一致，THE Cache_Manager SHALL 使用缓存文件而不重新下载，产生与重新下载相同的提取文本结果。
4. WHEN 远程文件大小与缓存文件大小不一致，THE Cache_Manager SHALL 从 FTP_Server 重新下载文件并更新缓存。
5. WHEN 无法确定远程文件大小（SIZE 命令失败），THE Cache_Manager SHALL 从 FTP_Server 重新下载文件。
6. IF Cache_Manager 无法将下载的文件写入 Cache_Directory（磁盘满、权限错误），THEN THE Cache_Manager SHALL 记录警告日志并继续使用刚下载的文件进行处理，不进行缓存。

### Requirement 10: 通过 uvx 部署

**User Story:** 作为开发者，我希望通过 `uvx` 部署 MCP 服务器，以便在无需手动管理依赖的情况下运行服务器。

#### Acceptance Criteria

1. THE MCP_Server SHALL 打包为与 `uvx` 兼容的 Python 项目，要求 Python 3.10 或更高版本，在 `pyproject.toml` 中指定。
2. THE MCP_Server SHALL 在 `pyproject.toml` 中定义控制台脚本入口点，使 `uvx` 能够定位并执行服务器进程。
3. WHEN 通过 `uvx` 执行，THE MCP_Server SHALL 启动并暴露 MCP 工具，无需用户手动安装依赖或创建虚拟环境（仍然需要通过 `.env` 文件进行环境配置，如 Requirement 5 所定义）。
4. THE MCP_Server SHALL 在符合 PEP 621 规范的 `pyproject.toml` 文件的 `[project.dependencies]` 部分声明所有运行时依赖。
