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

## 常见问题解决
- **配置文件格式问题**: 
  - 必须使用 `{"database_url": "...", "llm_configs": [...]}` 格式
  - 不要使用旧的嵌套格式 `{"llms": {...}}`，会导致配置无法正确加载
  - 可使用 `tools/convert_config.py` 脚本转换配置格式
  - 记得默认配置位置: `~/.config/acolyte/config.json`

- **LLM API URL与Provider设置**: 
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

- **会话管理工具与最佳实践**: 
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

- **HTTP客户端和错误处理**:
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

- **Prompt模板管理**:
  - 添加新的Prompt模板后必须运行`config sync-prompts`进行同步
  - `_v3.md`命名格式需要在PromptManager中特殊处理
  - 注意设置正确的prompt_dir路径，默认为项目根目录下的`prompt`目录
  
- **启动顺序**: 
  - 先启动API服务器: `uv run -m acolyte.main`
  - 导入LLM配置: `uv run -m acolyte.cli.main config import-config`
  - 同步提示词: `uv run -m acolyte.cli.main config sync-prompts`
  - 开始分析内容: `uv run -m acolyte.cli.main analyze ...`

- **日志系统配置**:
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
- CLI接口模块
  - 内容分析命令
  - 配置管理命令
  - 历史查询命令
  - LLM和Prompt管理命令
  - 富文本终端交互界面
- 配置管理
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

### 8. Web界面模块 [待开始]
- 使用Tailwind CSS和shadcn UI
- 内容提交表单
- LLM配置管理界面
- 结果可视化展示

### 9. 架构重构 [已完成]
- 服务层设计实现
  - 业务逻辑与API层分离
  - 标准化服务接口
  - 依赖注入模式
- 会话管理工具
  - 解决SQLAlchemy DetachedInstanceError问题
  - 同步/异步会话上下文管理器
  - 数据提取工具与会话装饰器
- LLM客户端架构升级
  - 基于抽象类和组合模式的设计
  - 异步客户端实现
  - 统一的错误处理和重试框架
  - 支持DeepSeek和Ollama接口
- 任务处理器重构
  - 策略模式实现
  - 专用处理器类型
  - 更好的错误处理

### 10. 下一步计划
- 单元测试和集成测试
  - 为重构后的组件添加测试用例
  - 验证重构后的系统稳定性
  - 测试错误处理和边缘情况
- Web界面模块
  - 使用Tailwind CSS和shadcn UI
  - 内容提交表单
  - LLM配置管理界面
  - 结果可视化展示
- 性能优化
  - 并行任务处理优化
  - 缓存机制
  - LLM响应解析性能提升
- 功能增强
  - 批量内容提交功能
  - 任务状态实时监控
  - LLM结果比较功能
  - 自定义评分方案