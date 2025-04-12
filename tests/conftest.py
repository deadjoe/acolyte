"""Pytest配置文件"""

import os
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import clear_mappers, sessionmaker

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acolyte.core.db.models import Base, LlmConfig, LlmRole, Prompt, Task, TaskResult, TaskStatus, ProcessingMode


@pytest.fixture(scope="function")
def in_memory_db():
    """创建内存数据库"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # 创建会话工厂
    session_factory = sessionmaker(bind=engine)

    # 返回会话工厂
    yield session_factory

    # 清理
    Base.metadata.drop_all(engine)
    clear_mappers()


@pytest.fixture(scope="function")
def db_session(in_memory_db):
    """创建数据库会话"""
    session = in_memory_db()

    # 返回会话
    yield session

    # 清理
    session.rollback()
    session.close()


@pytest.fixture
def sample_llm_configs(db_session):
    """创建示例LLM配置"""
    # 创建普通LLM
    normal_llm = LlmConfig()
    normal_llm.name = "Test Normal LLM"
    normal_llm.api_key = "test_key_1"
    normal_llm.base_url = "https://api.test1.com"
    normal_llm.model_name = "test-model-1"
    normal_llm.role = LlmRole.NORMAL
    normal_llm.is_default = True

    # 创建评论LLM
    reviewer_llm = LlmConfig()
    reviewer_llm.name = "Test Reviewer LLM"
    reviewer_llm.api_key = "test_key_2"
    reviewer_llm.base_url = "https://api.test2.com"
    reviewer_llm.model_name = "test-model-2"
    reviewer_llm.role = LlmRole.REVIEWER
    reviewer_llm.is_default = False

    db_session.add_all([normal_llm, reviewer_llm])
    db_session.commit()

    return {"normal": normal_llm, "reviewer": reviewer_llm}


@pytest.fixture
def sample_prompt(db_session):
    """创建示例提示词"""
    prompt = Prompt()
    prompt.version = "1.0"
    prompt.content = "Test prompt content"
    prompt.model_target = "test-model"
    prompt.is_active = True
    db_session.add(prompt)
    db_session.commit()

    return prompt


@pytest.fixture
def sample_task(db_session, sample_prompt, sample_llm_configs):
    """创建示例任务"""
    task = Task()
    task.content = "Test task content"
    task.processing_mode = ProcessingMode.SINGLE
    task.prompt_id = sample_prompt.id
    task.status = TaskStatus.PENDING
    task.created_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    db_session.add(task)
    db_session.commit()

    # 关联LLM
    task.llm_configs.append(sample_llm_configs["normal"])
    db_session.commit()

    # 关联评论LLM
    task.llm_configs.append(sample_llm_configs["reviewer"])
    db_session.commit()

    return task


@pytest.fixture
def sample_task_result(db_session, sample_task, sample_llm_configs):
    """创建示例任务结果"""
    task_result = TaskResult()
    task_result.task_id = sample_task.id
    task_result.llm_id = sample_llm_configs["normal"].id
    task_result.raw_response = "Test raw response"
    task_result.processed_result = "Test processed result"
    task_result.bias_index = 7.5
    task_result.misleading_index = 6.2
    task_result.hidden_intent_index = 4.8
    task_result.credibility_score = 60.5
    task_result.is_review_result = False
    task_result.created_at = datetime.now(timezone.utc)
    db_session.add(task_result)
    db_session.commit()

    return task_result


@pytest.fixture
def mock_db_session(db_session):
    """模拟数据库会话函数"""
    from acolyte.core.db import session as db_session_module

    # 保存原始函数
    original_run_in_session = db_session_module.run_in_session

    # 创建模拟函数
    async def mock_run_in_session(func):
        return await func(db_session)

    # 替换函数
    db_session_module.run_in_session = mock_run_in_session

    # 返回原始函数，以便恢复
    yield original_run_in_session

    # 恢复原始函数
    db_session_module.run_in_session = original_run_in_session
