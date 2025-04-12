# CLAUDE.md

## Project Overview
Acolyte是一个内容分析评估系统，专注于检测文本内容中的偏见、误导性和隐藏意图。系统支持通过Web界面、CLI和API三种方式提交内容，由单个或多个LLM进行分析评估。系统使用prompt目录中的模板进行内容分析，支持多LLM评议汇总和历史记录查询。

系统架构采用分层设计，包括API层、服务层、领域层和数据层，实现了业务逻辑和接口的清晰分离。支持Anthropic Claude、OpenAI GPT、Google Gemini、DeepSeek和Ollama等多种LLM供应商，具有完善的错误处理和自动重试机制，可灵活配置处理流程。

核心特色是综合偏见检测框架，包括语言层面分析、叙事结构分析、框架效应分析、事实准确性分析、逻辑谬误分析等多个维度，并提供量化评分系统计算内容的可信度。

## Style Guidelines
- 使用清晰的Python代码结构，遵循PEP 8规范
- 采用模块化设计，确保代码可测试性和可扩展性
- 应用设计模式：
  - 服务层模式：将业务逻辑从API路由中分离
  - 策略模式：用于任务处理器实现，支持多种处理策略
  - 工厂模式：用于LLM客户端创建，支持不同的提供商
  - 依赖注入：API路由通过参数接收服务实例
- 异步编程：使用asyncio和httpx实现异步API
- 前端使用Tailwind CSS和shadcn UI组件
- Python后端采用FastAPI框架
- 使用SQLite作为数据存储，通过SQLAlchemy ORM访问
- 命名规范:
  - 类名: PascalCase (如 `LlmManager`)
  - 函数/方法: snake_case (如 `process_content`)
  - 变量: snake_case (如 `task_result`)
  - 常量: UPPER_SNAKE_CASE (如 `DEFAULT_PROMPT_VERSION`)
- Prompt模板采用语义化版本号，并包含模型特定后缀

## 技术栈详情
- **包管理**: uv (不使用传统的pip，注意所有命令都应使用uv执行)
- **后端框架**: FastAPI + Uvicorn
- **数据库**: SQLite + SQLAlchemy ORM
- **CLI工具**: Click + Rich (终端富文本显示)
- **HTTP客户端**: HTTPX (异步支持)
- **异步编程**: asyncio (任务处理和多LLM并行请求)
- **架构模式**: 服务层设计模式、策略模式、工厂模式
- **LLM集成**:
  - Anthropic Claude API
  - OpenAI API
  - Google Gemini API
  - DeepSeek API
  - Ollama API (本地模型)
- **配置管理**: JSON配置文件 + 环境变量

## Prompt Guidelines
- 保持prompt目录作为模板主存储
- 遵循既定的模板结构和命名约定
  - 基本命名格式: `bias-detection-prompt_vX.Y.md`
  - 模型特定格式: `bias-detection-prompt_vX.Y_modelname.md`
  - 特殊格式: `bias-detection-prompt_v3.md` (Claude 3.7专用)
- 记录版本间的变更说明
- 确保模板适用于目标模型
- 偏见检测框架结构:
  - 分析前准备 (文章类型、目标受众等)
  - 偏见检测 (语言层面、叙事结构、框架效应)
  - 误导性内容检测 (事实准确性、逻辑谬误、混淆技巧)
  - 隐藏意图检测 (信息选择性呈现、情感操纵、隐形框架)
  - 量化评分系统 (偏见指数、误导性指数、隐藏意图指数、综合可信度)

## Commands
- **创建环境**: `uv venv`
- **安装依赖**: `uv pip install -r requirements.txt`
- **开发安装**: `uv pip install -e .`
- **启动服务**: `uv run -m acolyte.main`
- **CLI工具**: `uv run -m acolyte.cli.main [命令]`
- **代码格式**: `uv run -m black .` 和 `uv run -m isort .`
- **代码检查**: `uv run -m ruff check .` 和 `uv run -m mypy .`

## 环境变量
Acolyte CLI 支持以下环境变量来配置系统行为：

| 环境变量 | 用途 | 示例 |
|---------|------|------|
| `ACOLYTE_API_URL` | 指定API服务器的基础URL | `ACOLYTE_API_URL=http://192.168.1.100:8080/api` |
| `ACOLYTE_LOG_LEVEL` | 设置日志级别（debug, info, warning, error, critical） | `ACOLYTE_LOG_LEVEL=debug` |
| `ACOLYTE_LOG_TO_FILE` | 启用文件日志记录（0=禁用，1=启用） | `ACOLYTE_LOG_TO_FILE=1` |
| `ACOLYTE_LOG_DIR` | 指定日志文件存储目录 | `ACOLYTE_LOG_DIR=/path/to/logs` |
| `ACOLYTE_PORT` | 指定API服务器监听的端口 | `ACOLYTE_PORT=8080` |
| `ACOLYTE_PROMPT_DIR` | 指定提示词文件目录 | `ACOLYTE_PROMPT_DIR=./custom_prompts` |
| `ACOLYTE_CONFIG_DIR` | 指定配置文件目录 | `ACOLYTE_CONFIG_DIR=~/.config/acolyte` |
| `ACOLYTE_DATABASE_URL` | 指定数据库连接URL | `ACOLYTE_DATABASE_URL=sqlite:///custom_path.db` |

## 常见问题解决

### 配置文件格式问题
- 必须使用 `{"database_url": "...", "llm_configs": [...]}` 格式
- 不要使用旧的嵌套格式 `{"llms": {...}}`，会导致配置无法正确加载
- 可使用 `tools/convert_config.py` 脚本转换配置格式
- 记得默认配置位置: `~/.config/acolyte/config.json`

### LLM API URL与Provider设置
- Anthropic Claude: `https://api.anthropic.com/v1`
- OpenAI: `https://api.openai.com/v1`
- Google Gemini: `https://generativelanguage.googleapis.com/v1beta`
- DeepSeek: `https://api.deepseek.ai/v1`
- Ollama: `http://localhost:11434`（默认本地地址）
- 注意URL末尾的"/v1"部分对于Anthropic、OpenAI和DeepSeek是必须的
- 客户端代码中有处理URL格式的逻辑，见`base.py`中的`_normalize_base_url`方法
- provider属性会根据base_url和model_name自动推断，不需要显式设置
- 支持的provider值："anthropic"、"openai"、"gemini"、"deepseek"、"ollama"
- 本地模型使用Ollama运行时时，请确保Ollama服务已启动
- 对于不同的API错误，系统会进行自动重试和特殊处理：
  - 401错误：表示认证失败，检查API密钥是否正确
  - 429错误：表示请求过多，系统会自动等待并重试
  - 网络超时：系统会尝试重新连接并记录详细日志
  - API不可用：系统会提供详细的错误诊断信息

### 会话管理工具与最佳实践
- 系统提供了`SessionManager`工具类（`core/db/session.py`）用于处理会话管理：
  ```python
  # 同步上下文管理器
  with SessionManager.session_scope() as session:
      # 在会话内操作...

  # 异步上下文管理器
  async with SessionManager.async_session_scope() as session:
      # 在异步会话内操作...

  # 辅助函数
  data = SessionManager.extract_model_data(db_object)  # 从ORM对象提取纯数据

  # 会话装饰器
  @SessionManager.with_session
  def function_with_session(session, arg1, arg2):
      # 自动获取会话参数

  # 异步会话装饰器
  @SessionManager.async_with_session
  async def async_function_with_session(session, arg1, arg2):
      # 自动获取会话参数
  ```
- 不要在会话外使用数据库对象，特别是在异步操作中
- 使用服务层（`core/services/`）处理数据库操作，保持API路由简洁
- 若遇到SQLAlchemy DetachedInstanceError：
  - 使用`extract_model_data`提取纯数据而非保存ORM对象
  - 使用`join`预加载相关数据
  - 确保会话在相关数据使用完毕后才关闭
- 数据库操作中始终使用try-except包装并正确处理异常：
  - 出现异常时执行session.rollback()
  - 操作成功时执行session.commit()
  - 无论成功失败，finally中关闭session
- 异步任务处理中添加任务完成回调函数：
  ```python
  background_task = asyncio.create_task(process_task_async(task_id))
  background_task.add_done_callback(on_task_done)
  ```
- API中使用依赖注入获取会话：
  ```python
  @router.get("/items/{item_id}")
  async def read_item(item_id: int, session: AsyncSession = Depends(get_session)):
      # 使用注入的会话
  ```

### HTTP客户端和错误处理
- 系统提供了`HttpClientManager`类（`utils/http.py`）用于HTTP请求管理：
  ```python
  # 获取客户端
  client = HttpClientManager.get_client('anthropic')

  # 发送请求（带自动重试）
  response = await fetch(
      url='https://api.example.com/v1/chat',
      method='POST',
      json_data=payload,
      headers=headers,
      retry_codes=[429, 503]
  )
  ```
- LLM客户端使用重试框架（`core/llm/retry.py`）处理临时错误：
  ```python
  # 使用重试装饰器
  @retry_on_error(config=RetryConfig(max_retries=3))
  async def function_with_retry():
      # 失败自动重试
  ```
- 标准化的错误信息模型：
  - 使用`ErrorInfo`类表示统一的错误信息
  - 包含错误类型、消息、状态码、是否可重试等信息
- 所有客户端方法都为异步实现，支持并行请求处理
- 错误处理策略：
  - 对429（速率限制）错误使用指数退避算法
  - 对临时网络错误自动重试
  - 提供详细的错误诊断和日志记录

### Prompt模板管理
- 添加新的Prompt模板后必须运行`config sync-prompts`进行同步
- `_v3.md`命名格式需要在PromptManager中特殊处理
- 注意设置正确的prompt_dir路径，默认为项目根目录下的`prompt`目录

### 启动顺序
- 先启动API服务器: `uv run -m acolyte.main`
- 导入LLM配置: `uv run -m acolyte.cli.main config import-config`
- 同步提示词: `uv run -m acolyte.cli.main config sync-prompts`
- 开始分析内容: `uv run -m acolyte.cli.main analyze ...`

### 日志系统配置
- 通过环境变量`ACOLYTE_LOG_LEVEL`控制日志级别（debug, info, warning, error, critical）
- 设置`ACOLYTE_LOG_TO_FILE=1`启用文件日志
- 使用`ACOLYTE_LOG_DIR`指定日志文件目录
- 日志文件命名格式: `acolyte_YYYYMMDD_HHMMSS.log`
- 在代码中使用`get_logger("模块名")`获取日志记录器
- 不要混用print语句和日志系统，始终使用日志记录
- 日志记录最佳实践:
  - 关键操作前后使用INFO级别记录操作状态
  - 详细调试信息使用DEBUG级别记录
  - 所有异常必须使用ERROR或WARNING级别记录，并包含exc_info=True参数
  - 日志消息应该包含足够上下文，如任务ID、LLM名称、操作类型等
  - 使用结构化日志格式，便于后期分析: `logger.info(f"{operation}: {key1}={value1}, {key2}={value2}")`

## 配置管理
- 配置文件位于 `~/.config/acolyte/config.json`
- 可通过环境变量 `ACOLYTE_CONFIG_PATH` 指定其他位置
- 通过 `uv run -m acolyte.cli.main config export-config` 导出配置
- 通过 `uv run -m acolyte.cli.main config import-config` 导入配置
- LLM配置包含名称、API密钥、基础URL、模型名称等信息

## 开发进度

### 1. 目录结构创建 [已完成]
- 创建了基本目录结构，包括api、cli、web、core等模块
- 创建了基础代码框架

### 2. 数据库设计 [已完成]
- 定义了数据库模型
- 设计了表关系
- 包含评议者投票机制

### 3. 核心模块开发 [已完成]
- **服务层架构**
  - 明确的分层设计：API层、服务层、领域层、数据层
  - TaskService: 任务创建、处理和查询的业务逻辑
  - LlmService: LLM配置管理、测试和使用
  - PromptService: 提示词模板管理和同步
  - 业务逻辑与接口的清晰分离
  - 依赖注入与组合设计

- **LLM管理模块**
  - 基于组合模式的客户端架构
    - LlmClient 抽象基类
    - 基于工厂模式的提供商特定实现
  - 支持多种LLM提供商:
    - Anthropic Claude API
    - OpenAI GPT API
    - Google Gemini API
    - DeepSeek API
    - Ollama API (本地模型服务)
  - 异步客户端实现，支持并行处理
  - 强大的错误处理与重试机制
    - 自动重试临时错误
    - 指数退避策略
    - 统一的错误信息模型
  - 标准化响应解析器

- **Prompt管理模块**
  - 文件系统与数据库同步
  - 语义化版本管理
  - 模型特定Prompt支持
  - 特殊命名格式处理(`_v3.md`)
  - 提示词模板内容管理API

- **任务处理模块**
  - 基于策略模式的处理器架构:
    - BaseTaskProcessor 基类
    - SingleLlmProcessor 单LLM处理器
    - MultipleLlmProcessor 多LLM并行处理器
    - ReviewProcessor 评议处理器
  - 灵活的处理流程:
    - 单LLM分析
    - 多LLM并行分析
    - 多LLM评议（单评议者/多评议者投票）
  - 异步任务处理与状态管理
  - 批量任务操作API
  - 失败恢复与错误处理

- **API服务模块**
  - RESTful API接口设计
  - 请求参数验证与响应格式化
  - HTTP请求/响应日志中间件
  - 标准化错误响应

- **CLI接口模块**
  - 内容分析命令
  - 配置管理命令
  - 历史查询命令
  - LLM和Prompt管理命令
  - 富文本终端交互界面

- **配置管理**
  - JSON配置文件支持（标准化格式）
  - 配置导入导出功能
  - 配置格式转换工具
  - 环境变量支持

### 4. 偏见检测框架 [已完成]
- 综合偏见、误导性、隐藏意图检测框架
- 分类型分析（新闻报道、评论文章等）
- 量化评分系统（偏见指数、误导性指数、隐藏意图指数、综合可信度分数）
- 多维度检测（语言层面、叙事结构、框架效应等）

### 5. 工具和辅助脚本 [已完成]
- 配置格式转换工具
- 数据库记录检查工具
- 任务处理测试工具
- 结果显示工具

### 6. 日志系统实现 [已完成]
- 统一日志模块设计与实现 (utils/logging.py)
- 基于Python标准logging模块的分级日志系统
- 支持日志级别自定义（DEBUG、INFO、WARNING、ERROR、CRITICAL）
- 同时支持控制台和文件日志输出
- 全代码覆盖的日志系统：
  - API模块完整日志记录（请求、响应、异常）
  - LLM管理模块操作日志
  - 任务处理全流程日志
  - 配置管理日志支持
  - 命令行界面交互日志

### 7. 问题修复 [已完成]
- 修复会话管理问题和SQLAlchemy DetachedInstanceError
- 修复LLM Provider属性缺失和自动推断问题
- 修复配置文件格式问题
- 修复API URL格式问题
- 修复数据库模型循环依赖问题
- 修复LLM响应解析与分数提取问题
- 优化错误处理和日志记录
- 统一替换print语句为日志记录
- 实现API服务的HTTP请求/响应日志中间件
- 完善异步任务处理和会话管理机制
- 修复配置导入导出功能
  - 添加缺失的配置导入/导出API端点
  - 实现API层的配置文件管理功能
- 实现提示词管理完整功能
  - 修复提示词显示内容问题
  - 添加删除提示词的CLI命令
  - 改进提示词同步功能，支持自定义目录

### 8. Web界面模块 [待开始]
- 使用Tailwind CSS和shadcn UI
- 内容提交表单
- LLM配置管理界面
- 结果可视化展示

### 9. 架构重构 [已完成]
- **服务层设计实现**
  - 业务逻辑与API层分离
  - 标准化服务接口
  - 依赖注入模式

- **会话管理工具**
  - 解决SQLAlchemy DetachedInstanceError问题
  - 同步/异步会话上下文管理器
  - 数据提取工具与会话装饰器

- **LLM客户端架构升级**
  - 基于抽象类和组合模式的设计
  - 异步客户端实现
  - 统一的错误处理和重试框架
  - 支持DeepSeek和Ollama接口

- **任务处理器重构**
  - 策略模式实现
  - 专用处理器类型
  - 更好的错误处理

### 10. 最近进展 [2025-04-05]
- **添加设置默认LLM功能**
  - 添加设置默认LLM的API端点 `/llms/{llm_id}/set-default`
  - 在LlmService中添加`set_default_llm`方法
  - 在AcolyteClient中添加`set_default_llm`方法
  - 在CLI命令中添加`config set-default`命令
  - 更新README文档，添加新命令的使用说明
  - 完善默认LLM管理机制，支持通过CLI动态设置
- **改进LLM响应解析系统**
  - 重构ResponseParser类，实现更可靠的评分提取
  - 添加多种提取策略，提高提取成功率
  - 优先匹配"最终CS"格式，确保提取正确的综合可信度分数
  - 添加宽松模式匹配，支持列表项格式（如"• 加权BI = 4.95"）
  - 实现完整的结构化内容提取，包括背景、发现项、评估等
  - 添加详细的日志记录，帮助诊断提取问题
  - 修复综合可信度分数(CS)提取问题，确保从"最终CS"值而非计算公式提取

- **改进日志系统**
  - 添加更详细的日志记录，特别是在关键处理步骤
  - 记录提取评分的详细过程和结果
  - 记录任务处理的完整流程
  - 优化错误和警告日志，提供更多上下文信息

- **修复任务结果关联问题**
  - 确保任务的最终结果正确设置和获取
  - 改进BaseTaskProcessor._save_result方法中的日志记录
  - 修复datetime.utcnow()的使用，改为datetime.now(timezone.utc)

- **代码质量改进**
  - 清理未使用的导入
  - 统一日志格式和内容
  - 改进异常处理
  - 优化代码结构，遵循单一职责原则

### 11. 最新进展 [2025-04-05]
- **重构LLM响应解析系统**
  - 完全重构ResponseParser类，解决循环依赖问题
  - 创建通用的基础解析方法`parse_base_response`，所有特定LLM解析方法都调用此方法
  - 改进JSON解析逻辑，支持不同格式的JSON结构
  - 添加更详细的日志记录，便于追踪解析过程
  - 增强错误处理，提供更好的诊断信息
  - 优化代码结构，提高可维护性和可扩展性

- **修复JSON解析问题**
  - 修复OpenAIClient中的解析问题，确保正确调用ResponseParser
  - 解决嵌套JSON结构的提取问题，支持多种JSON格式
  - 添加更健壮的JSON验证和错误处理
  - 优化JSON字段映射，支持中英文字段名
  - 确保所有LLM（Claude、GPT-4o等）生成的JSON格式都能被正确解析

- **改进LLM客户端架构**
  - 修复OpenAIClient._parse_response方法，使其正确调用ResponseParser
  - 统一不同LLM客户端的响应解析逻辑
  - 添加更详细的日志记录，便于诊断问题
  - 优化错误处理，提供更好的错误信息

- **增强系统稳定性**
  - 添加更多的异常处理和错误恢复机制
  - 改进日志记录，提供更详细的诊断信息
  - 优化代码结构，减少重复代码
  - 确保系统在各种情况下都能正常工作

### 12. 最新进展 [2025-04-06]
- **优化CLI工具用户体验**
  - 为所有CLI命令添加API服务连接检查
  - 实现友好的错误信息显示，提供明确的操作建议
  - 改进`history list`命令的显示格式：
    - 按ID从小到大排序（最旧的在前），便于按时间顺序查看历史
    - 将UTC时间戳转换为本地时区的24小时制格式
    - 添加详细的时间转换日志，便于调试
  - 确保所有命令在API服务未启动时提供一致的错误提示

- **改进提示词系统**
  - 添加新的JSON格式提示词模板（v4版本）
  - 优化提示词中的量化评分部分，使用结构化JSON输出
  - 确保新提示词与所有支持的LLM兼容
  - 改进提示词目录配置，确保正确加载提示词文件

- **测试基础设施升级**
  - 更新测试脚本，使用uv替代传统的python命令
  - 改进pytest配置，添加asyncio相关设置
  - 更新单元测试，适应重构后的ResponseParser类
  - 确保所有测试在重构后仍然通过

- **配置管理优化**
  - 移除AppConfig中的prompt_dir字段，由PromptManager专门管理
  - 改进配置导入导出功能，确保不包含不必要的字段
  - 优化配置文件格式，提高可读性和可维护性

### 13. 最新进展 [2025-04-07]
- **优化Gemini LLM支持**
  - 增加Gemini API的maxOutputTokens参数从4000到8000，解决响应被截断的问题
  - 改进Gemini API请求格式，使其与最新的官方文档一致
    - 移除不再支持的`system_instruction`字段
    - 将系统提示词和用户提示词合并为一个文本，作为用户角色的消息
    - 添加`role`字段和正确的`parts`结构
    - 添加`responseMimeType`和`safetySettings`配置
  - 改进Gemini API错误处理，增强对配额限制和内容过滤的检测

- **修复LLM结果提取问题**
  - 解决了一个关键问题：不同的LLM客户端返回结构不一致
  - 统一了所有LLM客户端的返回结构，确保评分数据能够被正确提取
  - 修改Claude客户端的返回结构，使其与Gemini和OpenAI一致
  - 改进`_save_result_to_db`方法，增强对不同结构的兼容性

- **全面测试与文档化**
  - 创建了新的测试数据文件`tests/texts/test_news_article.txt`，用于测试LLM功能
  - 对所有三种LLM（Gemini、Claude和OpenAI）进行了全面测试，确保它们都能正确提取评分
  - 编写了详细的SingleLLM.md文档，分析了从选择Gemini LLM为默认LLM，然后执行analyze指令后的完整代码流转过程
  - 详细记录了问题定位和解决过程，为日后维护提供参考

### 14. 最新进展 [2025-04-08]
- **优化DeepSeek LLM支持**
  - 完全重建DeepSeek客户端实现，确保与其他LLM客户端保持一致
  - 修复DeepSeek客户端中的属性错误，将`api_base_url`改为`base_url`
  - 添加详细的日志记录和错误处理，便于调试和问题排查
  - 统一DeepSeek客户端的返回结构，确保评分数据能够被正确提取

- **改进LLM类型检测机制**
  - 修改`base.py`中的`_detect_provider`方法，添加对LLM名称的检查
  - 重构`client.py`中的`get_client_for_llm`函数，使用常量进行判断
  - 确保LLM类型检测的一致性，解决第三方托管LLM识别问题
  - 添加更详细的日志记录，便于追踪LLM类型检测过程

- **增强测试覆盖范围**
  - 创建新的测试文本`tests/texts/test_new_software.txt`，用于测试长文本处理能力
  - 对所有四种LLM（Claude、OpenAI、Gemini和DeepSeek）进行全面测试
  - 验证所有LLM都能正确处理内容并提取评分数据
  - 测试不同长度和内容类型的文本，确保系统稳定性

### 15. 最新进展 [2025-04-09]
- **修复Multiple模式异步处理问题**
  - 重构`MultipleLlmProcessor`中的异步处理逻辑，解决任务处理错误
  - 将`_create_llm_task`方法重命名为`_create_llm_coroutine`，直接返回协程而不是创建任务
  - 修改`_process_with_multiple_llms`方法，使用协程列表而不是任务列表
  - 确保`gather_with_concurrency`函数能够正确等待所有协程完成
  - 全面测试multiple模式，验证所有LLM都能正确处理内容并返回结果

- **增强CLI历史记录显示功能**
  - 重构`history show`命令，提供更丰富的选项和更好的用户体验
  - 添加`--all/--single`选项，允许用户选择显示所有LLM结果或仅显示最终结果
  - 添加`--llm`选项，允许用户指定要显示的LLM ID
  - 添加`--format`选项，支持表格、摘要和JSON三种显示格式
  - 优化时间显示格式，将UTC时间转换为本地时区的友好格式
  - 为multiple模式任务提供比较表格，便于比较不同LLM的评分结果

- **代码重构与优化**
  - 采用更规范的代码结构，将`history show`命令的实现移至单独的模块
  - 优化异步代码，确保正确的协程处理和任务等待
  - 改进错误处理，提供更详细的错误信息和日志记录
  - 确保代码的可维护性和可扩展性

- **文档更新**
  - 更新README.md和README_zh.md，添加新命令和选项的使用说明
  - 修复文档中的错误，确保命令示例的准确性
  - 添加multiple模式的详细说明，包括如何查看不同LLM的结果
  - 更新CLAUDE.md，记录最新的开发进展

- **修复Multiple模式下的类型不匹配问题**
  - 发现问题：在multiple模式下，Claude和Gemini的评分数据无法被正确提取和显示
  - 问题诊断：使用静态类型检查工具（mypy）发现`_create_llm_coroutine`方法声明返回类型为`Awaitable[Dict]`，但实际返回普通字典
  - 解决方案：采用最小化修改，将返回类型声明从`Awaitable[Dict]`改为`Dict`，与实际返回值匹配
  - 验证结果：修复后，multiple模式下所有LLM（包括Claude和Gemini）都能正确处理和返回结果
  - 长期建议：
    - 重命名方法为更准确反映其行为的名称，如`_process_with_llm`
    - 更新方法的文档字符串，准确描述其行为和返回值
    - 考虑更规范的修改，使异步执行流程更清晰
    - 为multiple模式添加全面的单元测试
    - 对整个异步处理逻辑进行全面的代码审查
  - 经验教训：
    - 静态类型检查工具（如mypy、pylint）对发现潜在问题非常有价值
    - 异步代码需要特别注意返回类型和执行流程的一致性
    - 方法名称应准确反映其实际行为，避免误导
    - 最小化修改在紧急情况下是有效的，但应考虑长期的代码健康

### 16. 技术债务清理 [2025-04-08]
- **修复Multiple模式LLM选择问题**
  - 发现问题：在multiple模式下，即使用户指定了特定的LLM ID，系统也会使用所有"normal"角色的LLM
  - 问题诊断：通过增强日志记录，发现`Task`对象创建后，其`llm_configs`属性已经自动关联了所有"normal"角色的LLM
  - 根本原因：在`_create_task_in_db`方法中，当尝试关联指定的LLM时，它们已经在`new_task.llm_configs`中，导致`new_llms`列表为空
  - 解决方案：修改`_create_task_in_db`方法，在关联指定的LLM之前，先清空`new_task.llm_configs`，然后直接设置为指定的LLM
  - 验证结果：修复后，multiple模式下系统只使用用户指定的LLM，而不是所有"normal"角色的LLM

### 17. 改进Ollama客户端实现 [2025-04-10]
- **优化Ollama客户端文档**
  - 更新OllamaClient类的文档字符串，提供更详细的功能描述和使用说明
  - 添加对Chat API支持的计划说明，这是Ollama推荐的API
  - 改进__init__方法的文档字符串，详细说明参数和初始化过程
  - 更新_normalize_base_url方法的文档字符串，说明URL标准化流程
  - 更新_check_api_key方法的文档字符串，解释Ollama不需要API密钥的原因
  - 更新process_content方法的文档字符串，详细说明处理流程和返回值
  - 更新_process_with_api方法的文档字符串，说明API请求流程
  - 更新_test_connection方法的文档字符串，说明连接测试流程

- **重构Ollama客户端代码**
  - 统一响应解析路径，使用ResponseParser.parse_ollama_response方法处理响应
  - 与其他LLM提供商（如OpenAI、Claude、DeepSeek）保持一致的调用路径
  - 统一导入风格，从相对导入改为绝对导入
  - 分开导入ResponseParser和ErrorHandler类，并从正确的模块导入

- **测试与验证**
  - 测试不同模型（llama3.3:latest、deepseek-r1:32b）的兼容性
  - 验证超时设置对大型模型的影响
  - 解决了响应解析路径的问题，使其与其他LLM提供商保持一致

- **代码优化与错误修复**
  - 添加@retry_on_error()装饰器到process_content方法，增强错误恢复能力
  - 修复导入问题，确保正确导入ErrorHandler类
  - 统一注释风格，将英文注释替换为中文注释，保持一致性
  - 优化代码结构，提高可读性和可维护性

- **增强日志系统用于问题诊断**
  - 设计并实现了全面的日志记录系统，用于跟踪任务创建和处理的完整流程
  - 在`_create_task_in_db`方法中添加详细日志，记录任务创建过程中的关键步骤和状态变化
  - 在`_get_llms_for_task`方法中添加详细日志，记录任务关联的LLM获取过程
  - 日志关键字设计：
    - 任务创建相关：
      - "任务创建后的初始LLM关联数量" - 记录任务创建后`llm_configs`的初始状态
      - "初始关联的LLM IDs" - 记录初始关联的LLM ID列表
      - "清空初始关联的LLM" - 记录清空操作的执行
      - "关联LLM(去重后)" - 记录去重后的LLM ID列表
      - "从数据库查询到" - 记录从数据库查询到的LLM对象数量
      - "查询到的LLM IDs" - 记录查询到的LLM ID列表
      - "直接设置LLM关联" - 记录设置操作的执行
      - "最终LLM关联数量" - 记录最终关联的LLM数量
      - "最终关联的LLM IDs" - 记录最终关联的LLM ID列表
      - "成功关联" - 记录成功关联的LLM数量
    - 任务处理相关：
      - "开始获取任务关联的LLM列表" - 记录开始获取LLM列表
      - "任务关联的LLM数量" - 记录任务关联的LLM数量
      - "任务关联的LLM IDs" - 记录任务关联的LLM ID列表
      - "提取LLM数据" - 记录LLM数据的提取过程
      - "最终返回个LLM数据对象" - 记录最终返回的LLM数据对象数量
      - "返回LLM IDs" - 记录返回的LLM ID列表
      - "开始并行处理" - 记录开始并行处理的LLM数量
      - "开始LLM处理" - 记录开始处理特定LLM

- **使用日志进行问题诊断的最佳实践**
  - 问题定位流程：
    1. 首先检查任务创建日志，确认初始LLM关联状态
    2. 检查LLM关联过程的日志，确认关联操作是否成功
    3. 检查任务处理日志，确认实际使用的LLM
    4. 检查数据库中的任务与LLM关联，验证日志与实际状态是否一致
  - 关键日志查询命令：
    - `grep "任务创建后的初始LLM关联数量" logs/acolyte_*.log` - 查看任务创建后的初始LLM关联状态
    - `grep "初始关联的LLM IDs" logs/acolyte_*.log` - 查看初始关联的LLM ID列表
    - `grep "清空初始关联的LLM" logs/acolyte_*.log` - 查看清空操作的执行情况
    - `grep "最终关联的LLM IDs" logs/acolyte_*.log` - 查看最终关联的LLM ID列表
    - `grep "任务关联的LLM数量" logs/acolyte_*.log` - 查看任务处理时关联的LLM数量
    - `grep "开始并行处理" logs/acolyte_*.log` - 查看并行处理的LLM数量
  - 数据库验证命令：
    - `sqlite3 acolyte.db "SELECT * FROM task_llm_association WHERE task_id=X;"` - 查看任务与LLM的关联关系

- **代码重构与优化**
  - 重命名`_create_llm_coroutine`方法为`_process_with_llm`，使其名称更准确地反映其行为
  - 更新方法的文档字符串，准确描述其行为和返回值
  - 优化异步任务处理逻辑，确保资源正确释放
  - 增强日志记录，提供更详细的诊断信息
## Multiple-with-Review 功能开发

### 功能概述
Multiple-with-Review 模式是一种高级分析模式，它首先使用多个 normal 角色的 LLM 对内容进行分析，然后使用 reviewer 角色的 LLM 对这些分析结果进行评议，选出最佳结果并提供综合建议。

### 开发过程中的关键问题与解决方案

#### 1. 任务与 LLM 关联管理
- **问题**：任务删除和清空时没有正确清除关联记录，导致数据库中存在孤立的关联记录
- **解决方案**：
  - 修改 `delete_task` 方法，添加清除任务与 LLM 关联和删除评审投票的逻辑
  - 修改 `clear_tasks` 方法，添加清除任务与 LLM 关联和删除评审投票的逻辑
  - 使用 SQL 语句直接清理数据库中的孤立关联记录

#### 2. LLM 角色匹配问题
- **问题**：LLM 角色匹配区分大小写，导致在某些情况下无法正确识别 LLM 的角色
- **解决方案**：
  - 在 `_get_llms_for_task` 和 `_get_reviewers_for_task` 方法中，使用 `LlmRole` 枚举类型来匹配角色，而不是直接使用字符串
  - 这样可以避免大小写敏感问题，提高系统的健壮性

#### 3. 评议处理器中的协程处理问题
- **问题**：在 `_single_reviewer_mode` 方法中，使用 `run_in_executor` 来运行 `client.process_content`，但没有正确处理返回的协程
- **解决方案**：
  - 使用 `await` 直接等待 `client.process_content` 方法的结果，而不是使用 `run_in_executor`
  - 修复相关的导入和未使用的变量

#### 4. Reviewer 角色 LLM 参与内容分析问题
- **问题**：Reviewer 角色的 LLM 也参与了内容分析，而不是只评估其他 LLM 的分析结果
- **解决方案**：
  - 修改 `_get_llms_for_task` 方法，使其只返回 normal 角色的 LLM
  - 修改 `_create_review_prompt` 方法，使其更明确地要求 reviewer 角色的 LLM 评估其他 LLM 的分析结果，而不是直接对原始文章进行分析和打分

#### 5. 结果显示不区分普通结果和评议结果
- **问题**：在 `history show` 命令中，系统显示了所有与任务相关的结果，包括评议结果，但没有区分普通结果和评议结果
- **解决方案**：
  - 修改 `show_all_llm_results` 函数，在表格中添加一个"类型"列，清楚地标识了每个结果的类型（分析结果或评议结果）

### 测试与验证
- 对 single、multiple 和 multiple_with_review 三种模式进行了全面测试
- 验证了 normal 角色的 LLM 正确参与内容分析
- 验证了 reviewer 角色的 LLM 不再生成自己的评分，而是评估其他 LLM 的分析结果
- 验证了结果显示清晰区分了分析结果和评议结果

### 成果
- Multiple-with-Review 模式现在可以正常工作，提供了更高质量的分析结果
- 系统的健壮性和可用性得到了提升
- 用户体验得到了改善，结果显示更加清晰和易于理解

## 单元测试改进 [2025-04-12]

### 测试框架升级
- 使用 pytest 和 pytest-asyncio 进行单元测试
- 添加 pytest-cov 用于测试覆盖率分析
- 配置 pytest.ini 文件，设置 asyncio 模式为 STRICT

### 修复的测试问题
- **ReviewProcessor 测试**：
  - 修复 `_parse_vote_result` 方法测试，添加正确的参数和 side_effect
  - 修复 `_save_votes` 测试，确保正确模拟数据库会话
  - 修复 process 相关测试，通过直接模拟 process 方法
  - 修复 `test_create_reviewer_task` 测试，简化异步模拟

- **LlmClient 测试**：
  - 修复 URL 检测测试，确保正确匹配 DeepSeek 和 Ollama 客户端
  - 更新 URL 模式以匹配实际实现
  - 修复 `test_get_headers` 测试，添加缺少的 `_get_headers` 方法

- **LlmConfig 测试**：
  - 修复 `test_import_llm_config_from_file` 测试，正确模拟 LlmConfig 模型

### 测试覆盖率分析
- 总体覆盖率：50%（4924 行代码中有 2485 行未被测试覆盖）
- 覆盖率最高的模块：
  - `acolyte/__init__.py`: 100%
  - `acolyte/cli/main.py`: 100%
  - `acolyte/core/llm/client.py`: 100%
  - `acolyte/core/llm/constants.py`: 100%
- 覆盖率最低的模块：
  - `acolyte/cli/history_show.py`: 16%
  - `acolyte/cli/commands.py`: 20%
  - `acolyte/core/task/processor.py`: 21%
  - `acolyte/core/services/task_service.py`: 23%

### 未来测试改进计划
- 提高 CLI 模块覆盖率，特别是 `commands.py` 和 `history_show.py`
- 增强服务层测试，包括 `task_service.py`、`prompt_service.py` 和 `llm_service.py`
- 改进任务处理器测试，特别是 `processor.py` 和 `base.py`
- 增强异步工具测试，包括 `async_utils.py` 和 `http.py`
- 解决协程未等待的警告和 SQLAlchemy 外键依赖关系警告
