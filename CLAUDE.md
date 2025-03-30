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

- **LLM API URL格式**: 
  - Anthropic Claude: `https://api.anthropic.com/v1`
  - OpenAI: `https://api.openai.com/v1`
  - Google Gemini: `https://generativelanguage.googleapis.com/v1beta`
  - 注意URL末尾的"/v1"部分对于Anthropic和OpenAI是必须的
  - 客户端代码中有处理URL格式的逻辑，见`client.py`中的`_normalize_base_url`方法

- **会话管理问题**: 
  - 不要在会话外使用数据库对象，特别是在异步操作中
  - 异步操作中创建和使用数据库对象必须在同一个会话上下文中
  - 在需要跨异步函数使用数据库对象时，可用变量传递对象值而非对象本身
  - 参考`direct_task_process.py`脚本中的解决方案

- **Prompt模板管理**:
  - 添加新的Prompt模板后必须运行`config sync-prompts`进行同步
  - `_v3.md`命名格式需要在PromptManager中特殊处理
  - 注意设置正确的prompt_dir路径，默认为项目根目录下的`prompt`目录
  
- **启动顺序**: 
  - 先启动API服务器: `uv run -m acolyte.main`
  - 导入LLM配置: `uv run -m acolyte.cli.main config import-config`
  - 同步提示词: `uv run -m acolyte.cli.main config sync-prompts`
  - 开始分析内容: `uv run -m acolyte.cli.main analyze ...`

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
- Prompt管理模块
  - 文件系统与数据库同步
  - 版本管理
  - 模型特定Prompt支持
  - Prompt内容查看功能
- 任务处理模块
  - 单LLM处理流程
  - 多LLM并行处理
  - 评议流程
    - 单评议者模式
    - 多评议者投票模式
- API服务模块
  - RESTful API接口
  - 任务管理接口
  - LLM配置接口
  - Prompt管理接口
- CLI接口模块
  - 内容分析命令
  - 配置管理命令
  - 历史查询命令
  - LLM和Prompt管理命令
- 配置管理
  - JSON配置文件支持（标准化格式）
  - 配置导入导出功能 
  - 配置格式转换工具

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

### 6. 问题修复 [已完成]
- 修复会话管理问题
- 修复配置文件格式问题
- 修复API URL格式问题
- 修复数据库模型循环依赖问题

### 7. Web界面模块 [待开始]
- 使用Tailwind CSS和shadcn UI
- 内容提交表单
- LLM配置管理界面
- 结果可视化展示