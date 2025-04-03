"""
数据库模型单元测试

测试数据库模型的关系、约束和基本功能。
"""
import pytest
from datetime import datetime

from acolyte.core.db.models import (
    Base, LlmConfig, LlmRole, ProcessingMode, Prompt,
    Task, TaskResult, TaskStatus
)


class TestDatabaseModels:
    """数据库模型测试用例"""

    def test_llm_config_creation(self, db_session):
        """测试创建LLM配置"""
        # 创建LLM配置
        llm = LlmConfig()
        llm.name = "Test LLM"
        llm.description = "Test LLM Description"
        llm.api_key = "test_api_key"
        llm.base_url = "https://api.test.com"
        llm.model_name = "test-model"
        llm.role = LlmRole.NORMAL
        llm.is_default = True

        # 保存到数据库
        db_session.add(llm)
        db_session.commit()

        # 从数据库查询
        saved_llm = db_session.query(LlmConfig).filter_by(name="Test LLM").first()

        # 验证结果
        assert saved_llm is not None
        assert saved_llm.name == "Test LLM"
        assert saved_llm.description == "Test LLM Description"
        assert saved_llm.api_key == "test_api_key"
        assert saved_llm.base_url == "https://api.test.com"
        assert saved_llm.model_name == "test-model"
        assert saved_llm.role == LlmRole.NORMAL
        assert saved_llm.is_default is True
        assert isinstance(saved_llm.created_at, datetime)
        assert isinstance(saved_llm.updated_at, datetime)

    def test_prompt_creation(self, db_session):
        """测试创建Prompt"""
        # 创建Prompt
        prompt = Prompt()
        prompt.version = "1.0"
        prompt.model_target = "general"
        prompt.content = "This is a test prompt"
        prompt.description = "Test Prompt Description"
        prompt.is_active = True
        prompt.file_path = "/path/to/prompt.md"

        # 保存到数据库
        db_session.add(prompt)
        db_session.commit()

        # 从数据库查询
        saved_prompt = db_session.query(Prompt).filter_by(version="1.0").first()

        # 验证结果
        assert saved_prompt is not None
        assert saved_prompt.version == "1.0"
        assert saved_prompt.model_target == "general"
        assert saved_prompt.content == "This is a test prompt"
        assert saved_prompt.description == "Test Prompt Description"
        assert saved_prompt.is_active is True
        assert saved_prompt.file_path == "/path/to/prompt.md"
        assert isinstance(saved_prompt.created_at, datetime)
        assert isinstance(saved_prompt.updated_at, datetime)

    def test_task_creation(self, db_session):
        """测试创建任务"""
        # 创建Prompt
        prompt = Prompt()
        prompt.version = "1.0"
        prompt.model_target = "general"
        prompt.content = "This is a test prompt"
        db_session.add(prompt)
        db_session.flush()

        # 创建任务
        task = Task()
        task.content = "This is a test content"
        task.processing_mode = ProcessingMode.SINGLE
        task.status = TaskStatus.PENDING
        task.prompt_id = prompt.id

        # 保存到数据库
        db_session.add(task)
        db_session.commit()

        # 从数据库查询
        saved_task = db_session.query(Task).filter_by(content="This is a test content").first()

        # 验证结果
        assert saved_task is not None
        assert saved_task.content == "This is a test content"
        assert saved_task.processing_mode == ProcessingMode.SINGLE
        assert saved_task.status == TaskStatus.PENDING
        assert saved_task.prompt_id == prompt.id
        assert saved_task.final_result_id is None
        assert isinstance(saved_task.created_at, datetime)
        assert isinstance(saved_task.updated_at, datetime)

        # 验证关系
        assert saved_task.prompt is not None
        assert saved_task.prompt.version == "1.0"

    def test_task_result_creation(self, db_session):
        """测试创建任务结果"""
        # 创建LLM配置
        llm = LlmConfig()
        llm.name = "Test LLM"
        llm.api_key = "test_api_key"
        llm.base_url = "https://api.test.com"
        llm.model_name = "test-model"
        db_session.add(llm)

        # 创建任务
        task = Task()
        task.content = "This is a test content"
        task.processing_mode = ProcessingMode.SINGLE
        task.status = TaskStatus.PENDING
        db_session.add(task)
        db_session.flush()

        # 创建任务结果
        task_result = TaskResult()
        task_result.task_id = task.id
        task_result.llm_id = llm.id
        task_result.raw_response = "This is a raw response"
        task_result.processed_result = "This is a processed result"
        task_result.bias_index = 7.5
        task_result.misleading_index = 6.2
        task_result.hidden_intent_index = 4.8
        task_result.credibility_score = 60.5
        task_result.is_review_result = False

        # 保存到数据库
        db_session.add(task_result)
        db_session.commit()

        # 从数据库查询
        saved_result = db_session.query(TaskResult).filter_by(task_id=task.id).first()

        # 验证结果
        assert saved_result is not None
        assert saved_result.task_id == task.id
        assert saved_result.llm_id == llm.id
        assert saved_result.raw_response == "This is a raw response"
        assert saved_result.processed_result == "This is a processed result"
        assert saved_result.bias_index == 7.5
        assert saved_result.misleading_index == 6.2
        assert saved_result.hidden_intent_index == 4.8
        assert saved_result.credibility_score == 60.5
        assert saved_result.is_review_result is False
        assert isinstance(saved_result.created_at, datetime)

        # 验证关系
        assert saved_result.task is not None
        assert saved_result.llm_config is not None
        assert saved_result.task.content == "This is a test content"
        assert saved_result.llm_config.name == "Test LLM"

    def test_task_llm_association(self, db_session):
        """测试任务与LLM的多对多关系"""
        # 创建LLM配置
        llm1 = LlmConfig()
        llm1.name = "Test LLM 1"
        llm1.api_key = "test_api_key_1"
        llm1.base_url = "https://api.test.com"
        llm1.model_name = "test-model-1"

        llm2 = LlmConfig()
        llm2.name = "Test LLM 2"
        llm2.api_key = "test_api_key_2"
        llm2.base_url = "https://api.test.com"
        llm2.model_name = "test-model-2"
        llm2.role = LlmRole.REVIEWER

        db_session.add_all([llm1, llm2])

        # 创建任务
        task = Task()
        task.content = "This is a test content"
        task.processing_mode = ProcessingMode.MULTIPLE_WITH_REVIEW
        task.status = TaskStatus.PENDING

        # 关联LLM
        task.llm_configs.append(llm1)
        task.llm_configs.append(llm2)

        # 保存到数据库
        db_session.add(task)
        db_session.commit()

        # 从数据库查询
        saved_task = db_session.query(Task).filter_by(content="This is a test content").first()

        # 验证结果
        assert saved_task is not None
        assert len(saved_task.llm_configs) == 2
        assert any(llm.name == "Test LLM 1" for llm in saved_task.llm_configs)
        assert any(llm.name == "Test LLM 2" for llm in saved_task.llm_configs)

        # 验证反向关系
        llm1_from_db = db_session.query(LlmConfig).filter_by(name="Test LLM 1").first()
        assert len(llm1_from_db.tasks) == 1
        assert llm1_from_db.tasks[0].content == "This is a test content"

    def test_task_final_result(self, db_session):
        """测试任务最终结果关系"""
        # 创建LLM配置
        llm = LlmConfig()
        llm.name = "Test LLM"
        llm.api_key = "test_api_key"
        llm.base_url = "https://api.test.com"
        llm.model_name = "test-model"
        db_session.add(llm)

        # 创建任务
        task = Task()
        task.content = "This is a test content"
        task.processing_mode = ProcessingMode.SINGLE
        task.status = TaskStatus.PROCESSING
        db_session.add(task)
        db_session.flush()

        # 创建任务结果
        task_result = TaskResult()
        task_result.task_id = task.id
        task_result.llm_id = llm.id
        task_result.bias_index = 7.5
        task_result.misleading_index = 6.2
        task_result.hidden_intent_index = 4.8
        task_result.credibility_score = 60.5
        db_session.add(task_result)
        db_session.flush()

        # 设置最终结果
        task.final_result_id = task_result.id
        task.status = TaskStatus.COMPLETED
        db_session.commit()

        # 从数据库查询
        saved_task = db_session.query(Task).filter_by(id=task.id).first()

        # 验证结果
        assert saved_task is not None
        assert saved_task.final_result_id == task_result.id
        assert saved_task.status == TaskStatus.COMPLETED
