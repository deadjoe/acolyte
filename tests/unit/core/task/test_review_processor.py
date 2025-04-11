"""
ReviewTaskProcessor单元测试

测试ReviewTaskProcessor的核心功能和业务规则，特别是multiple_with_review功能。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acolyte.core.db.models import LlmRole, ProcessingMode, TaskStatus
from acolyte.core.task.processors.review import MultipleLlmProcessor as ReviewProcessor


class TestReviewProcessor:
    """ReviewProcessor类的测试用例"""

    @pytest.fixture
    def processor(self):
        """创建ReviewProcessor实例"""
        return ReviewProcessor()

    @pytest.fixture
    def mock_session_run(self):
        """模拟run_in_session函数"""
        with patch("acolyte.core.task.processors.review.run_in_session") as mock:
            # 配置mock以异步执行传入的函数
            async def side_effect(func):
                # 创建一个模拟的session
                session = MagicMock()
                # 调用传入的函数并返回结果
                return await func(session)

            mock.side_effect = side_effect
            yield mock

    @pytest.mark.asyncio
    async def test_process(self, processor):
        """测试process方法"""
        # 模拟_get_task_data方法
        task_data = {
            "id": 1,
            "content": "Test content",
            "processing_mode": ProcessingMode.MULTIPLE_WITH_REVIEW,
            "status": TaskStatus.PENDING,
        }
        processor._get_task_data = AsyncMock(return_value=task_data)

        # 模拟_update_task_status方法
        processor._update_task_status = AsyncMock(return_value=True)

        # 模拟_process_multiple_with_review_mode方法
        result_ids = [2, 3, 4]
        final_result_id = 5
        processor._process_multiple_with_review_mode = AsyncMock(
            return_value=(result_ids, final_result_id)
        )

        # 执行测试
        result = await processor.process(1)

        # 验证结果
        assert result["success"] is True
        assert result["task_id"] == 1
        assert result["result_ids"] == result_ids
        assert result["final_result_id"] == final_result_id

        # 验证方法调用
        processor._get_task_data.assert_called_once_with(1)
        processor._update_task_status.assert_any_call(1, TaskStatus.PROCESSING)
        processor._update_task_status.assert_any_call(1, TaskStatus.COMPLETED)
        processor._process_multiple_with_review_mode.assert_called_once_with(1, task_data)

    @pytest.mark.asyncio
    async def test_process_error(self, processor):
        """测试process方法处理错误的情况"""
        # 模拟_get_task_data方法抛出异常
        error = Exception("Test error")
        processor._get_task_data = AsyncMock(side_effect=error)

        # 模拟_handle_error方法
        error_result = {
            "success": False,
            "task_id": 1,
            "error": "Test error",
        }
        processor._handle_error = AsyncMock(return_value=error_result)

        # 执行测试
        result = await processor.process(1)

        # 验证结果
        assert result["success"] is False
        assert result["task_id"] == 1
        assert "Test error" in result["error"]

        # 验证方法调用
        processor._get_task_data.assert_called_once_with(1)
        processor._handle_error.assert_called_once_with(1, error)

    @pytest.mark.asyncio
    async def test_process_multiple_with_review_mode(self, processor):
        """测试_process_multiple_with_review_mode方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
            "processing_mode": ProcessingMode.MULTIPLE_WITH_REVIEW,
        }

        # 模拟_process_normal_llms方法
        normal_result_ids = [2, 3]
        processor._process_normal_llms = AsyncMock(return_value=normal_result_ids)

        # 模拟_process_reviewer_llms方法
        review_result_ids = [4, 5]
        processor._process_reviewer_llms = AsyncMock(return_value=review_result_ids)

        # 模拟_calculate_final_result方法
        final_result_id = 6
        processor._calculate_final_result = AsyncMock(return_value=final_result_id)

        # 执行测试
        result_ids, final_id = await processor._process_multiple_with_review_mode(task_id, task_data)

        # 验证结果
        assert result_ids == normal_result_ids + review_result_ids
        assert final_id == final_result_id

        # 验证方法调用
        processor._process_normal_llms.assert_called_once_with(task_id, task_data)
        processor._process_reviewer_llms.assert_called_once_with(task_id, task_data, normal_result_ids)
        processor._calculate_final_result.assert_called_once_with(task_id, normal_result_ids + review_result_ids)

    @pytest.mark.asyncio
    async def test_process_normal_llms(self, processor):
        """测试_process_normal_llms方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
        }

        # 模拟_get_llms_for_task方法
        llms = [
            {"id": 2, "name": "LLM 1", "role": LlmRole.NORMAL.value},
            {"id": 3, "name": "LLM 2", "role": LlmRole.NORMAL.value},
        ]
        processor._get_llms_for_task = AsyncMock(return_value=llms)

        # 模拟_process_with_llm方法
        result_ids = [4, 5]
        processor._process_with_llm = AsyncMock(side_effect=result_ids)

        # 执行测试
        result = await processor._process_normal_llms(task_id, task_data)

        # 验证结果
        assert result == result_ids

        # 验证方法调用
        processor._get_llms_for_task.assert_called_once_with(task_id, task_data)
        assert processor._process_with_llm.call_count == 2
        processor._process_with_llm.assert_any_call(task_id, task_data, llms[0])
        processor._process_with_llm.assert_any_call(task_id, task_data, llms[1])

    @pytest.mark.asyncio
    async def test_process_reviewer_llms(self, processor):
        """测试_process_reviewer_llms方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
        }
        normal_result_ids = [2, 3]

        # 模拟_get_reviewers_for_task方法
        reviewers = [
            {"id": 4, "name": "Reviewer 1", "role": LlmRole.REVIEWER.value},
            {"id": 5, "name": "Reviewer 2", "role": LlmRole.REVIEWER.value},
        ]
        processor._get_reviewers_for_task = AsyncMock(return_value=reviewers)

        # 模拟_process_with_reviewer方法
        review_result_ids = [6, 7]
        processor._process_with_reviewer = AsyncMock(side_effect=review_result_ids)

        # 执行测试
        result = await processor._process_reviewer_llms(task_id, task_data, normal_result_ids)

        # 验证结果
        assert result == review_result_ids

        # 验证方法调用
        processor._get_reviewers_for_task.assert_called_once_with(task_id, task_data)
        assert processor._process_with_reviewer.call_count == 2
        processor._process_with_reviewer.assert_any_call(task_id, task_data, reviewers[0], normal_result_ids)
        processor._process_with_reviewer.assert_any_call(task_id, task_data, reviewers[1], normal_result_ids)

    @pytest.mark.asyncio
    async def test_get_reviewers_for_task(self, processor, mock_session_run):
        """测试_get_reviewers_for_task方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
        }

        # 模拟查询结果
        mock_llm1 = MagicMock()
        mock_llm1.id = 2
        mock_llm1.name = "Reviewer 1"
        mock_llm1.role = LlmRole.REVIEWER.value

        mock_llm2 = MagicMock()
        mock_llm2.id = 3
        mock_llm2.name = "Reviewer 2"
        mock_llm2.role = LlmRole.REVIEWER.value

        # 模拟TaskLlm关联
        mock_task_llm1 = MagicMock()
        mock_task_llm1.llm = mock_llm1
        mock_task_llm2 = MagicMock()
        mock_task_llm2.llm = mock_llm2

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_task_llm1, mock_task_llm2]

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value = mock_query

        # 配置extract_model_data
        with patch("acolyte.core.task.processors.review.extract_model_data") as mock_extract:
            mock_extract.side_effect = lambda obj, **kwargs: {
                "id": obj.id,
                "name": obj.name,
                "role": obj.role,
            }

            # 配置mock_session_run的返回值
            expected_reviewers = [
                {"id": 2, "name": "Reviewer 1", "role": LlmRole.REVIEWER.value},
                {"id": 3, "name": "Reviewer 2", "role": LlmRole.REVIEWER.value},
            ]
            mock_session_run.return_value = expected_reviewers

            # 执行测试
            result = await processor._get_reviewers_for_task(task_id, task_data)

            # 验证结果
            assert result == expected_reviewers
            # 验证mock_session_run被调用
            mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_reviewer(self, processor):
        """测试_process_with_reviewer方法"""
        # 模拟数据
        task_id = 1
        task_data = {
            "id": task_id,
            "content": "Test content",
        }
        reviewer = {
            "id": 2,
            "name": "Test Reviewer",
            "provider": "test",
            "model_name": "test-model",
        }
        normal_result_ids = [3, 4]

        # 模拟_get_normal_results方法
        normal_results = [
            {
                "id": 3,
                "llm_id": 5,
                "llm_name": "LLM 1",
                "raw_response": "Response 1",
                "processed_result": "Processed 1",
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
            },
            {
                "id": 4,
                "llm_id": 6,
                "llm_name": "LLM 2",
                "raw_response": "Response 2",
                "processed_result": "Processed 2",
                "bias_index": 8.1,
                "misleading_index": 5.9,
                "hidden_intent_index": 3.7,
                "credibility_score": 65.2,
            },
        ]
        processor._get_normal_results = AsyncMock(return_value=normal_results)

        # 模拟_create_review_prompt方法
        review_prompt = "Review prompt"
        processor._create_review_prompt = MagicMock(return_value=review_prompt)

        # 模拟_create_llm_client方法
        mock_client = MagicMock()
        mock_client.process_content = AsyncMock(return_value={
            "raw_response": "Review response",
            "processed_result": "Review processed result",
            "best_result_id": 4,
            "best_llm_name": "LLM 2",
        })
        processor._create_llm_client = MagicMock(return_value=mock_client)

        # 模拟_save_review_result方法
        review_result_id = 7
        processor._save_review_result = AsyncMock(return_value=review_result_id)

        # 执行测试
        result = await processor._process_with_reviewer(task_id, task_data, reviewer, normal_result_ids)

        # 验证结果
        assert result == review_result_id

        # 验证方法调用
        processor._get_normal_results.assert_called_once_with(normal_result_ids)
        processor._create_review_prompt.assert_called_once_with(task_data["content"], normal_results)
        processor._create_llm_client.assert_called_once_with(reviewer)
        mock_client.process_content.assert_called_once_with(review_prompt)
        processor._save_review_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_normal_results(self, processor, mock_session_run):
        """测试_get_normal_results方法"""
        # 模拟数据
        result_ids = [1, 2]

        # 模拟查询结果
        mock_result1 = MagicMock()
        mock_result1.id = 1
        mock_result1.llm_id = 3
        mock_result1.llm_config = MagicMock()
        mock_result1.llm_config.name = "LLM 1"
        mock_result1.raw_response = "Response 1"
        mock_result1.processed_result = "Processed 1"
        mock_result1.bias_index = 7.5
        mock_result1.misleading_index = 6.2
        mock_result1.hidden_intent_index = 4.8
        mock_result1.credibility_score = 60.5

        mock_result2 = MagicMock()
        mock_result2.id = 2
        mock_result2.llm_id = 4
        mock_result2.llm_config = MagicMock()
        mock_result2.llm_config.name = "LLM 2"
        mock_result2.raw_response = "Response 2"
        mock_result2.processed_result = "Processed 2"
        mock_result2.bias_index = 8.1
        mock_result2.misleading_index = 5.9
        mock_result2.hidden_intent_index = 3.7
        mock_result2.credibility_score = 65.2

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_result1, mock_result2]

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value = mock_query

        # 配置mock_session_run的返回值
        expected_results = [
            {
                "id": 1,
                "llm_id": 3,
                "llm_name": "LLM 1",
                "raw_response": "Response 1",
                "processed_result": "Processed 1",
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
            },
            {
                "id": 2,
                "llm_id": 4,
                "llm_name": "LLM 2",
                "raw_response": "Response 2",
                "processed_result": "Processed 2",
                "bias_index": 8.1,
                "misleading_index": 5.9,
                "hidden_intent_index": 3.7,
                "credibility_score": 65.2,
            },
        ]
        mock_session_run.return_value = expected_results

        # 执行测试
        result = await processor._get_normal_results(result_ids)

        # 验证结果
        assert result == expected_results
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()

    def test_create_review_prompt(self, processor):
        """测试_create_review_prompt方法"""
        # 模拟数据
        content = "Original content"
        results = [
            {
                "id": 1,
                "llm_id": 3,
                "llm_name": "LLM 1",
                "processed_result": "Processed 1",
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
            },
            {
                "id": 2,
                "llm_id": 4,
                "llm_name": "LLM 2",
                "processed_result": "Processed 2",
                "bias_index": 8.1,
                "misleading_index": 5.9,
                "hidden_intent_index": 3.7,
                "credibility_score": 65.2,
            },
        ]

        # 执行测试
        prompt = processor._create_review_prompt(content, results)

        # 验证结果
        assert "Original content" in prompt
        assert "LLM 1" in prompt
        assert "LLM 2" in prompt
        assert "Processed 1" in prompt
        assert "Processed 2" in prompt
        assert "60.5" in prompt
        assert "65.2" in prompt

    @pytest.mark.asyncio
    async def test_save_review_result(self, processor):
        """测试_save_review_result方法"""
        # 模拟数据
        task_id = 1
        reviewer_id = 2
        review_result = {
            "raw_response": "Review response",
            "processed_result": "Review processed result",
            "best_result_id": 3,
            "best_llm_name": "LLM 1",
        }

        # 模拟_save_result方法
        result_id = 4
        processor._save_result = AsyncMock(return_value=result_id)

        # 执行测试
        result = await processor._save_review_result(task_id, reviewer_id, review_result)

        # 验证结果
        assert result == result_id

        # 验证方法调用
        processor._save_result.assert_called_once_with(
            task_id,
            reviewer_id,
            {
                "raw_response": review_result["raw_response"],
                "processed_result": review_result["processed_result"],
                "is_review_result": True,
                "bias_index": None,
                "misleading_index": None,
                "hidden_intent_index": None,
                "credibility_score": None,
            }
        )

    @pytest.mark.asyncio
    async def test_calculate_final_result(self, processor):
        """测试_calculate_final_result方法"""
        # 模拟数据
        task_id = 1
        result_ids = [2, 3, 4, 5, 6]  # 包括普通结果和评议结果

        # 模拟_get_best_result_from_reviews方法
        best_result_id = 3
        processor._get_best_result_from_reviews = AsyncMock(return_value=best_result_id)

        # 模拟_update_task_final_result方法
        processor._update_task_final_result = AsyncMock(return_value=True)

        # 执行测试
        result = await processor._calculate_final_result(task_id, result_ids)

        # 验证结果
        assert result == best_result_id

        # 验证方法调用
        processor._get_best_result_from_reviews.assert_called_once_with(result_ids)
        processor._update_task_final_result.assert_called_once_with(task_id, best_result_id)

    @pytest.mark.asyncio
    async def test_get_best_result_from_reviews(self, processor, mock_session_run):
        """测试_get_best_result_from_reviews方法"""
        # 模拟数据
        result_ids = [1, 2, 3, 4, 5]  # 包括普通结果和评议结果

        # 模拟查询结果 - 评议结果
        mock_review1 = MagicMock()
        mock_review1.id = 4
        mock_review1.is_review_result = True
        mock_review1.processed_result = '{"best_result_id": 2, "best_llm_name": "LLM 2"}'

        mock_review2 = MagicMock()
        mock_review2.id = 5
        mock_review2.is_review_result = True
        mock_review2.processed_result = '{"best_result_id": 2, "best_llm_name": "LLM 2"}'

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.all.return_value = [mock_review1, mock_review2]

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value = mock_query

        # 配置mock_session_run的返回值
        mock_session_run.return_value = 2  # 返回投票最多的结果ID

        # 执行测试
        result = await processor._get_best_result_from_reviews(result_ids)

        # 验证结果
        assert result == 2
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_final_result(self, processor, mock_session_run):
        """测试_update_task_final_result方法"""
        # 模拟数据
        task_id = 1
        result_id = 2

        # 模拟查询结果
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.final_result_id = None

        # 配置查询结果
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = mock_task

        # 配置session
        mock_session = MagicMock()
        mock_session.query.return_value = mock_query

        # 配置mock_session_run的返回值
        mock_session_run.return_value = True

        # 执行测试
        result = await processor._update_task_final_result(task_id, result_id)

        # 验证结果
        assert result is True
        # 验证mock_session_run被调用
        mock_session_run.assert_called_once()
