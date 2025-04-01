# Acolyte Content Analysis System Design Document

## 1. System Overview
Acolyte is a content analysis and evaluation system focused on detecting bias, misleading content, and hidden intent in text. The system supports content submission through Web interface, CLI, and API, which is then analyzed by single or multiple LLMs. The system supports result aggregation, multi-LLM review, and history query functionality.

## 2. System Architecture
The system adopts a front-end and back-end separation architecture:
- **Backend**: Python-based API service using FastAPI
- **Frontend**: Web interface based on Tailwind CSS and shadcn UI components
- **CLI Client**: Command-line tool using Click and Rich for rich text display
- **Storage**: SQLite database with SQLAlchemy ORM
- **Logging**: Comprehensive unified logging system with multi-level support

## 3. Core Function Modules
### 3.1 LLM Management Module
- LLM configuration management (name, API key, base URL, model name)
- LLM connection testing
- Default LLM settings
- Reviewer role LLM settings
- LLM status monitoring and error handling

### 3.2 Content Processing Module
- Single LLM processing workflow
- Multiple LLM parallel processing workflow
- Multiple LLM review aggregation process
  - Single reviewer mode: A designated reviewer processes all evaluation results
  - Multiple reviewer voting mode: Multiple reviewers assess the results, with the most voted result being adopted
- Prompt template management and version control

### 3.3 Task Management Module
- Task creation and execution
- Task status tracking
- Historical task storage and query
- Task result visualization

### 3.4 API Service Module
- RESTful API interfaces
- Multi-language support (Chinese by default, English optional)
- Request/response logging
- Error handling and reporting

### 3.5 Logging System
- Unified logging module with configurable levels
- Console and file-based logging outputs
- Structured log format with contextual information
- Component-specific logging integration
- Diagnostic support for error analysis

## 4. Database Design
### 4.1 Table Structure
- **llm_configs**: LLM configuration information (name, API key, base URL, model name, etc.)
- **prompts**: Prompt templates (version, content, description, creation time, etc.)
- **tasks**: Task records (ID, submission time, text content, processing method, status, etc.)
- **task_results**: Task results (task ID, LLM ID, raw response, processed results, scores, etc.)
- **task_llms**: Association between tasks and LLMs (task ID, LLM ID list, whether reviewer)
- **reviewer_votes**: Reviewer voting records (task ID, reviewer ID, result ID voted for)

### 4.2 Database Relationships
- One-to-many relationship between tasks and task_results
- Many-to-many relationship between tasks and llm_configs (through task_llms)
- One-to-many relationship between prompts and tasks
- One-to-many relationship between llm_configs and task_results

## 5. Prompt Management Strategy
### 5.1 Storage Methods
- **File System**: Maintain the prompt directory as the primary storage for easy version control and direct editing
- **Database Mirror**: Synchronize the latest prompt versions to the database for convenient API access
- **Version Tracking**: Record different versions in the database to support historical version queries and rollbacks
- **Model-Specific Prompts**: Support variant prompts optimized for specific LLM models

### 5.2 Prompt Loading Process
1. Scan the prompt directory to get the latest versions during system startup
2. Compare with database records and synchronize any updates to the database
3. Prioritize reading from the database during runtime for efficient access
4. Support special format detection (like the Claude-specific `_v3.md` format)
5. Log all prompt loading and synchronization operations

## 6. Interface Design
### 6.1 Web Interface
- Content submission and processing method selection
- LLM configuration management
- Historical task query and result display
- Multi-language support switching
- Result visualization with metrics and charts

### 6.2 API Interface
- `/api/tasks`: Create tasks, get task status and results
- `/api/llms`: LLM configuration management
- `/api/prompts`: Prompt template management
- `/api/config`: System configuration management
- `/api/tasks/{id}/results`: Get detailed analysis results for a specific task

### 6.3 CLI Commands
- `analyze`: Content analysis and evaluation
- `config`: LLM and system configuration management
- `history`: Historical record query
- `show`: Display specific task results
- `llm`: LLM management operations
- `prompt`: Prompt template operations

## 7. Implementation Process
### 7.1 Task Submission Process
1. Receive user-submitted content and processing method selection
2. Select corresponding LLMs based on processing method (single/multiple)
3. Retrieve the latest prompt template (with model-specific targeting if available)
4. Parallel call to LLMs to process content
5. If review is needed, enter the review process:
   - Single reviewer: Send all results to a designated reviewer LLM for aggregation
   - Multiple reviewers:
     a. Send all results to each reviewer
     b. Collect votes from each reviewer
     c. Count voting results and select the result with the most votes
6. Parse results and extract key information and scores
7. Format returned results and store task records
8. Log all operations and capture any errors with contextual information

### 7.2 Result Presentation Strategy
- **Web Interface**: Beautifully formatted text + graphical score display
- **CLI**: Concise text format with neat layout using Rich library
- **API**: Standard JSON response with consistently structured data
- **Logs**: Detailed system logs for diagnostics and monitoring

### 7.3 Error Handling Strategy
1. API-level error handling with appropriate HTTP status codes
2. Comprehensive error logging with traceback information
3. User-friendly error messages with actionable suggestions
4. Graceful degradation when partial system failures occur
5. Automatic retry for transient API failures

## 8. Extensibility Design
- **Batch Processing Interface**: Reserved API design for batch text processing
- **Multi-language Support**: Internationalization architecture design
- **Custom Evaluation Framework**: Support for user-defined prompt templates
- **Plugin System**: Reserved plugin mechanism for future feature extensions
- **Advanced Analytics**: Framework for aggregating results across multiple analyses
- **API Integration**: Support for integration with external content management systems
- **Custom Logging**: Configurable logging outputs for different deployment environments

## 9. Logging System Design
### 9.1 Logging Infrastructure
- Centralized logging configuration in `utils/logging.py`
- Environment variable control: `ACOLYTE_LOG_LEVEL`, `ACOLYTE_LOG_TO_FILE`, `ACOLYTE_LOG_DIR`
- Support for multiple output destinations (console, file)
- Different log formats for different outputs (simplified for console, detailed for files)

### 9.2 Log Levels
- **DEBUG**: Detailed development and diagnostic information
- **INFO**: General operational events and milestones
- **WARNING**: Potential issues that don't prevent operation
- **ERROR**: Errors that allow the application to continue running
- **CRITICAL**: Severe errors that may cause application failure

### 9.3 Module-Specific Logging
- API request/response logging
- Database transaction logging
- LLM client interaction logging
- Task processing workflow logging
- Configuration management logging
- CLI command execution logging