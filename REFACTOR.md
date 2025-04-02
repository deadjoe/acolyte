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

### Week 1: Foundation
- Implement session management utilities
- Create service layer structure
- Begin API module restructuring

### Week 2: Core Logic
- Complete task processor refactoring
- Enhance LLM client base class
- Extract shared components

### Week 3: LLM Integration
- Fix OpenAI and Gemini implementations
- Add DeepSeek LLM support
- Start Ollama API integration

### Week 4: Refinement
- Complete all LLM integrations
- Optimize LLM management
- Conduct comprehensive testing
- Finalize documentation

## Success Criteria

1. All identified code complexity issues resolved
2. Clear separation of concerns in architecture
3. All LLM integrations working correctly
4. Improved error handling and logging
5. Codebase ready for future enhancements
6. Documentation updated to reflect changes