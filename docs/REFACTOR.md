# Acolyte Code Refactoring Plan

## Project Overview

Acolyte is a content analysis system focused on detecting bias, misleading information, and hidden intent in text content. The system supports content submission through Web, CLI, and API interfaces, with analysis performed by single or multiple LLMs. The current codebase has several areas for improvement in terms of code complexity, architectural design, and maintainability.

## Identified Issues

1. **Session Management in Async Context**
   - SQLAlchemy DetachedInstanceError in async operations
   - Complex session handling in routes.py and processor.py

2. **Code Complexity**
   - Lengthy inline async processing in routes.py (process_task_async)
   - Complex task processing logic in processor.py
   - Repetitive code in LLM client implementations

3. **API Module Organization**
   - Business logic mixed with routing in routes.py
   - No clear service layer separation

4. **LLM Integration Issues**
   - OpenAI and Gemini integrations not functioning correctly
   - Need for additional LLM support (DeepSeek, Ollama)
   - LLM management needs optimization

5. **Code Quality and Error Handling**
   - Inconsistent error handling
   - Incomplete logging in some areas
   - Opportunity for improved testing coverage

## Refactoring Goals

1. Improve code maintainability and readability
2. Enhance system reliability and error handling
3. Simplify addition of new features and LLM integrations
4. Ensure all LLM integrations work correctly
5. Establish clear architectural patterns

## Refactoring Plan

### Phase 1: Foundation Improvements

#### Task 1.1: Create Session Management Utilities
- Create `acolyte/core/db/session.py` with session management utilities
- Implement async-friendly session patterns
- Create helper functions for common database operations
- Address DetachedInstanceError issues

#### Task 1.2: API Module Restructuring
- Create service layer in `acolyte/core/services/`
- Implement `task_service.py` and `llm_service.py`
- Move business logic from routes.py to service layer
- Simplify route handlers to focus on request/response handling

### Phase 2: Core Logic Optimization

#### Task 2.1: Task Processor Refactoring
- Create `BaseTaskProcessor` class with shared functionality
- Implement specialized processors for different processing modes
- Extract common patterns and reduce code duplication
- Integrate with new session management utilities

#### Task 2.2: LLM Client Architecture Improvement
- Enhance `LlmClient` base class functionality
- Extract shared response parsing and error handling logic
- Create utility classes for HTTP operations and retry logic
- Simplify vendor-specific implementations

### Phase 3: LLM Functionality Enhancement

#### Task 3.1: Verify and Fix Existing LLM Integrations
- Create comprehensive test cases for each LLM provider
- Fix OpenAI and Gemini integration issues
- Improve error handling and response parsing
- Ensure consistent behavior across providers

#### Task 3.2: Add New LLM Support
- Implement DeepSeek LLM client
- Implement Ollama API support
- Create documentation for adding new LLM integrations
- Validate new integrations with test cases

#### Task 3.3: Optimize LLM Management
- Improve LLM configuration handling
- Enhance provider auto-detection
- Simplify LLM selection logic
- Add support for LLM capability detection

### Phase 4: Quality Assurance

#### Task 4.1: Code Quality Enhancement
- Add type hints throughout the codebase
- Implement consistent error handling patterns
- Enforce coding standards with automated tools
- Reduce function complexity and length

#### Task 4.2: Logging System Review
- Ensure comprehensive logging coverage
- Standardize log message format and content
- Add context information to log messages
- Verify log levels are appropriate

#### Task 4.3: Testing Infrastructure
- Create unit test framework
- Implement integration tests for critical paths
- Add test fixtures and mocks for LLM testing
- Establish continuous testing workflow

## Implementation Strategy

### Directory Structure Changes

```
acolyte/
  core/
    services/           # New service layer
      __init__.py
      task_service.py   # Task processing service
      llm_service.py    # LLM management service
    db/
      session.py        # Session management helpers
    utils/
      http.py           # HTTP request utilities
      async_utils.py    # Async processing utilities
    llm/
      base.py           # Enhanced base client
      response.py       # Response parsing utilities
      providers/        # Provider-specific implementations
```

### Implementation Approach

1. **Incremental Development**
   - Focus on small, testable changes
   - Maintain backward compatibility
   - Verify functionality after each step

2. **Vertical Slice Implementation**
   - Complete end-to-end flow for one processing mode first
   - Extend to other modes after validation
   - Ensures functional system throughout the process

3. **Continuous Integration**
   - Frequent commits with focused changes
   - Regular testing of the complete system
   - Avoid long-lived feature branches

4. **Documentation**
   - Update technical documentation with architectural changes
   - Add inline documentation for complex logic
   - Create examples for common usage patterns

## Execution Plan

### Phase 1: Foundation Improvements (Completed)
- Implemented session management utilities in `acolyte/core/db/session.py`
- Created service layer structure with `TaskService`, `LlmService`, and `PromptService`
- Restructured API module to separate business logic from routing
- Enhanced error handling mechanisms throughout the application

### Phase 2: Core Logic Optimization (Completed)
- Refactored task processors with `BaseTaskProcessor` and specialized implementations
- Enhanced LLM client architecture with improved base class
- Extracted shared response parsing logic into `ResponseParser` class
- Implemented robust error handling and retry mechanisms

### Phase 3: LLM Functionality Enhancement (Completed)
- Added support for DeepSeek and Ollama LLM providers
- Refactored Ollama client to standardize response parsing path and import style
- Fixed issues with existing LLM integrations
- Improved LLM configuration handling and management
- Enhanced response parsing for different LLM output formats
- Completely rebuilt DeepSeek client implementation for better consistency
- Improved LLM type detection mechanism for third-party hosted LLMs
- Unified response structure across all LLM clients

### Phase 4: Quality Assurance and CLI Improvements (Completed)
- Improved logging system with standardized formats and appropriate levels
- Enhanced CLI interface with better command organization
- Added `status` command to check API service status
- Implemented user-friendly error handling in CLI
  - Added API connection checks to all CLI commands
  - Provided clear error messages with actionable suggestions
  - Ensured consistent error handling across all commands
- Improved CLI history display
  - Changed sorting order to ascending by ID (oldest first)
  - Converted UTC timestamps to local timezone with 24-hour format
  - Added detailed time conversion logging for debugging
- Enhanced `history show` command for multiple mode
  - Added `--all/--single` option to control result display
  - Added `--llm` option to view specific LLM results
  - Added `--format` option with table, summary, and JSON formats
  - Implemented comparison table for multiple LLM results
  - Ensured consistent time formatting across all displays
- Fixed multiple mode async processing
  - Refactored `MultipleLlmProcessor` to use coroutines instead of tasks
  - Improved parallel processing with proper async/await patterns
  - Enhanced error handling in multiple LLM processing
- Updated documentation to reflect architectural changes

## Implementation Highlights

### Session Management and Service Layer
- Created robust session management utilities to address DetachedInstanceError issues
- Implemented service layer with clear separation of concerns
- Moved business logic from routes to dedicated service classes

### Task Processing Improvements
- Refactored task processors with inheritance-based architecture
- Fixed task result association issues
- Improved error handling during task processing
- Enhanced logging throughout the task lifecycle

### LLM Response Parsing
- Implemented sophisticated response parsing with multiple extraction strategies
- Added support for various LLM output formats including JSON structures
- Fixed credibility score extraction issues
- Enhanced error handling for malformed responses
- Resolved circular reference bug in OpenAI response parsing
- Improved JSON extraction with support for nested objects and arrays
- Added support for mixed Chinese/English field names in JSON responses
- Implemented fallback regex patterns for non-JSON formatted responses
- Unified response structure across all LLM clients for consistent data extraction
- Optimized response parsing for DeepSeek LLM with improved error handling

### CLI Enhancements
- Improved command organization with OrderedGroup
- Added status command for API service monitoring
- Implemented user-friendly error messages
- Enhanced connection handling between CLI and API
- Added API connection checks to all CLI commands
- Improved history list display with better sorting and time formatting
- Converted UTC timestamps to local timezone with 24-hour format
- Enhanced `history show` command for multiple mode
  - Added `--all/--single` option to control result display
  - Added `--llm` option to view specific LLM results
  - Added `--format` option with table, summary, and JSON formats
  - Implemented comparison table for multiple LLM results
  - Ensured consistent time formatting across all displays
- Fixed multiple mode async processing
  - Refactored `MultipleLlmProcessor` to use coroutines instead of tasks
  - Improved parallel processing with proper async/await patterns
  - Enhanced error handling in multiple LLM processing

### Documentation Updates
- Updated DESIGN.md with detailed LLM response parsing architecture
- Maintained CLAUDE.md with current development progress
- Enhanced inline documentation throughout the codebase
- Added detailed descriptions of JSON parsing strategies
- Updated test infrastructure documentation

## Success Criteria Achievement

1. ✅ **Code Complexity**: Significantly reduced through refactoring and architectural improvements
2. ✅ **Separation of Concerns**: Implemented clear service layer and processor hierarchy
3. ✅ **LLM Integrations**: Added new providers and fixed existing integration issues
4. ✅ **Error Handling**: Enhanced throughout the application with user-friendly messages
5. ✅ **Future Readiness**: Established patterns for easy addition of new features
6. ✅ **Documentation**: Updated to reflect architectural changes and implementation details