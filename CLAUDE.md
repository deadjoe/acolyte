# CLAUDE.md

## Project Overview
Acolyte是一个内容分析评估系统，专注于检测文本内容中的偏见、误导性和隐藏意图。系统支持通过Web界面、CLI和API三种方式提交内容，由单个或多个LLM进行分析评估。系统使用prompt目录中的模板进行内容分析，支持多LLM评议汇总和历史记录查询。系统支持Anthropic Claude、OpenAI GPT和Google Gemini三大主流LLM供应商，可灵活配置审核流程。

核心特色是综合偏见检测框架，包括语言层面分析、叙事结构分析、框架效应分析、事实准确性分析、逻辑谬误分析等多个维度，并提供量化评分系统计算内容的可信度。

## Style Guidelines
- 使用清晰的Python代码结构，遵循PEP 8规范
- 采用模块化设计，确保代码可测试性和可扩展性
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
- **LLM集成**:
  - Anthropic Claude API
  - OpenAI API
  - Google Gemini API
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
  - 注意URL末尾的"/v1"部分对于Anthropic和OpenAI是必须的
  - 客户端代码中有处理URL格式的逻辑，见`client.py`中的`_normalize_base_url`方法
  - provider属性会根据base_url和model_name自动推断，不需要显式设置
  - 支持的provider值："anthropic"、"openai"、"gemini"
  - 对于不同的API错误，系统会进行特殊处理：
    - 401错误：表示认证失败，检查API密钥是否正确
    - 429错误：表示请求过多，系统会自动等待并重试
    - 网络超时：系统会记录详细日志并友好提示

- **会话管理问题**: 
  - 不要在会话外使用数据库对象，特别是在异步操作中
  - 异步操作中创建和使用数据库对象必须在同一个会话上下文中
  - 在需要跨异步函数使用数据库对象时，可用变量传递对象值而非对象本身
  - 若遇到SQLAlchemy DetachedInstanceError，确保使用外部变量存储会话外需要的数据，而不是直接引用会话对象
  - 参考`direct_task_process.py`脚本中的解决方案和`routes.py`中的`process_task_async`函数实现
  - 数据库操作中始终使用try-except包装并正确处理异常：
    - 出现异常时执行session.rollback()
    - 操作成功时执行session.commit()
    - 无论成功失败，finally中关闭session
  - 在异步上下文中访问懒加载属性时务必预先加载(eager loading)或在会话内完成访问
  - 异步任务处理中添加任务完成回调函数，确保任务状态始终正确：
    ```python
    background_task = asyncio.create_task(process_task_async(task_id))
    background_task.add_done_callback(on_task_done)
    ```

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
- LLM管理模块
  - LLM配置管理
  - 支持多种LLM (Anthropic Claude、OpenAI、Google Gemini)
  - LLM删除功能
  - 根据模型名称和API URL自动推断provider类型
  - LLM连接测试功能
- Prompt管理模块
  - 文件系统与数据库同步
  - 版本管理
  - 模型特定Prompt支持
  - Prompt内容查看功能
  - 支持特殊命名格式(`_v3.md`)的处理
- 任务处理模块
  - 单LLM处理流程
  - 多LLM并行处理
  - 评议流程
    - 单评议者模式
    - 多评议者投票模式
  - 异步任务处理和状态管理
  - 批量任务管理（查询、删除）
- API服务模块
  - RESTful API接口
  - 任务管理接口
  - LLM配置接口
  - Prompt管理接口
  - HTTP请求/响应日志中间件
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

### 9. 下一步计划
- 完善API错误处理机制 [部分完成]
  - 已实现详细的异常处理和日志记录
  - 仍需优化错误响应格式和用户反馈
- 增强结果展示功能
- 添加批量内容提交功能
  - 已实现单内容的多LLM并行处理
  - 已实现批量任务管理（如批量删除）
  - 需要实现一次提交多篇内容的批量分析
- 任务状态实时监控
- 性能优化与压力测试
- 整合多个LLM结果的比较功能
- 自定义评分方案