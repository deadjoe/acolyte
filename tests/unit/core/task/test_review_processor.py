"""
ReviewProcessor单元测试

测试ReviewProcessor的核心功能和业务规则，特别是multiple_with_review功能。
"""

import time
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from acolyte.core.db.models import LlmConfig, LlmRole, TaskStatus
from acolyte.core.task.processors.review import ReviewProcessor


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

    @pytest.fixture
    def mock_multiple_processor(self):
        """模拟MultipleLlmProcessor"""
        with patch("acolyte.core.task.processors.review.MultipleLlmProcessor") as mock_class:
            # 创建模拟实例
            mock_instance = MagicMock()
            mock_instance.process = AsyncMock()
            # 设置process方法的返回值
            mock_instance.process.return_value = {
                "success": True,
                "task_id": 1,
                "result_ids": [1, 2, 3],
            }
            # 设置类实例化返回模拟实例
            mock_class.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_task_data(self):
        """模拟任务数据"""
        return {
            "id": 1,
            "content": "测试内容",
            "status": TaskStatus.PENDING.value,
            "created_at": time.time(),
            "updated_at": time.time(),
        }

    @pytest.fixture
    def mock_results(self):
        """模拟任务结果"""
        return [
            {
                "id": 1,
                "llm_id": 1,
                "raw_response": "LLM 1的分析结果",
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
            },
            {
                "id": 2,
                "llm_id": 2,
                "raw_response": "LLM 2的分析结果",
                "bias_index": 6.8,
                "misleading_index": 5.5,
                "hidden_intent_index": 3.9,
                "credibility_score": 65.2,
            },
            {
                "id": 3,
                "llm_id": 3,
                "raw_response": "LLM 3的分析结果",
                "bias_index": 8.1,
                "misleading_index": 7.0,
                "hidden_intent_index": 5.2,
                "credibility_score": 55.8,
            },
        ]

    @pytest.fixture
    def mock_reviewers(self):
        """模拟评议者数据"""
        return [
            {
                "id": 4,
                "api_key": "test_api_key_1",
                "base_url": "https://api.test.com",
                "model_name": "test-model-1",
                "role": LlmRole.REVIEWER.value,
                "is_default": False,
            },
            {
                "id": 5,
                "api_key": "test_api_key_2",
                "base_url": "https://api.test.com",
                "model_name": "test-model-2",
                "role": LlmRole.REVIEWER.value,
                "is_default": False,
            },
        ]

    @pytest.mark.asyncio
    async def test_process_with_multiple_processor_error(self, processor):
        """测试多LLM处理器错误情况"""
        # 准备测试数据
        task_id = 1
        error_message = "处理失败"

        # 模拟multiple_processor.process返回失败
        processor.multiple_processor.process = AsyncMock(
            return_value={"success": False, "error": error_message}
        )

        # 模拟_update_task_status返回成功
        processor._update_task_status = AsyncMock(return_value=True)

        # 执行测试
        result = await processor.process(task_id)

        # 验证结果
        assert result["success"] is False
        assert result["error"] == f"多LLM处理失败: {error_message}"

        # 验证方法调用
        assert processor._update_task_status.call_count == 2
        processor._update_task_status.assert_has_calls(
            [call(task_id, TaskStatus.PROCESSING), call(task_id, TaskStatus.FAILED)],
            any_order=False,
        )

    @pytest.mark.asyncio
    async def test_process_with_no_reviewers(self, processor):
        """测试没有评议者的情况"""
        # 准备测试数据
        task_id = 1
        result_ids = [1, 2, 3]
        results = [{"id": i} for i in result_ids]

        # 模拟multiple_processor.process返回成功
        processor.multiple_processor.process = AsyncMock(
            return_value={
                "success": True,
                "task_id": task_id,
                "result_ids": result_ids,
                "results": results,
            }
        )

        # 模拟_get_reviewers_for_task返回空列表
        processor._get_reviewers_for_task = AsyncMock(return_value=[])

        # 模拟_update_task_status返回成功
        processor._update_task_status = AsyncMock(return_value=True)

        # 模拟_update_status返回成功
        with patch("acolyte.core.task.processors.base.run_in_session") as mock_run_in_session:
            mock_run_in_session.return_value = True

        # 执行测试
        result = await processor.process(task_id)

        # 验证结果
        assert result["success"] is True
        assert result["task_id"] == task_id
        assert result["result_ids"] == result_ids
        assert result["results"] == results

    @pytest.mark.asyncio
    async def test_process_with_single_reviewer(self, processor):
        """测试单个评议者的情况"""
        # 准备测试数据
        task_id = 1

        # 模拟multiple_processor.process返回成功
        processor.multiple_processor.process = AsyncMock(
            return_value={"success": True, "task_id": task_id, "result_ids": [1, 2, 3]}
        )

        # 模拟_get_reviewers_for_task返回单个评议者
        reviewer = {"id": 1, "name": "Reviewer 1"}
        processor._get_reviewers_for_task = AsyncMock(return_value=[reviewer])

        # 模拟_update_task_status返回成功
        processor._update_task_status = AsyncMock(return_value=True)

        # 模拟_update_status返回成功
        with patch("acolyte.core.task.processors.base.run_in_session") as mock_run_in_session:
            mock_run_in_session.return_value = True

        # 模拟_single_reviewer_mode返回成功
        processor._single_reviewer_mode = AsyncMock(
            return_value={"success": True, "task_id": task_id, "final_result_id": 2}
        )

        # 执行测试
        result = await processor.process(task_id)

        # 验证结果
        assert result["success"] is True
        assert result["task_id"] == task_id
        assert result["final_result_id"] == 2

        # 验证_single_reviewer_mode被调用
        processor._single_reviewer_mode.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_multiple_reviewers(self, processor):
        """测试多个评议者的情况"""
        # 准备测试数据
        task_id = 1
        result_ids = [1, 2, 3]
        results = [{"id": i} for i in result_ids]

        # 模拟multiple_processor.process返回成功
        processor.multiple_processor.process = AsyncMock(
            return_value={
                "success": True,
                "task_id": task_id,
                "result_ids": result_ids,
                "results": results,
            }
        )

        # 模拟_get_reviewers_for_task返回多个评议者
        reviewers = [{"id": 1, "name": "Reviewer 1"}, {"id": 2, "name": "Reviewer 2"}]
        processor._get_reviewers_for_task = AsyncMock(return_value=reviewers)

        # 模拟_multiple_reviewer_vote_mode返回成功
        vote_result = {
            "success": True,
            "task_id": task_id,
            "final_result_id": 2,
            "vote_counts": {1: 1, 2: 2},
            "valid_votes": 2,
        }
        processor._multiple_reviewer_vote_mode = AsyncMock(return_value=vote_result)

        # 模拟_update_task_status返回成功
        processor._update_task_status = AsyncMock(return_value=True)

        # 模拟_get_task_with_content返回内容
        processor._get_task_with_content = AsyncMock(return_value={"content": "测试内容"})

        # 执行测试
        result = await processor.process(task_id)

        # 验证结果
        assert result == vote_result

        # 验证方法调用
        processor._multiple_reviewer_vote_mode.assert_called_once_with(
            task_id=task_id, task_content="测试内容", reviewers=reviewers, result_ids=result_ids
        )

    @pytest.mark.asyncio
    async def test_single_reviewer_mode(self, processor, mock_results):
        """测试_single_reviewer_mode方法"""
        # 准备测试数据
        task_id = 1
        task_content = "测试内容"
        reviewer = {
            "id": 4,
            "name": "Test Reviewer",
            "api_key": "test_api_key",
            "base_url": "https://api.test.com",
            "model_name": "test-model",
            "role": LlmRole.REVIEWER,
            "is_default": False,
        }
        result_ids = [1, 2, 3]

        # 模拟方法
        processor._get_task_results = AsyncMock(return_value=mock_results)
        processor._create_review_prompt = MagicMock(return_value="测试评议提示词")
        # 创建LlmConfig对象
        llm_config = LlmConfig()
        llm_config.name = reviewer["name"]
        llm_config.api_key = reviewer["api_key"]
        llm_config.base_url = reviewer["base_url"]
        llm_config.model_name = reviewer["model_name"]
        llm_config.role = reviewer["role"]
        processor._rebuild_llm_config = MagicMock(return_value=llm_config)
        processor._update_task_status = AsyncMock(return_value=True)
        processor._save_result = AsyncMock(return_value=5)  # 返回评议结果的ID

        # 模拟LLM客户端
        mock_client = MagicMock()
        mock_client.process_content = AsyncMock(
            return_value={
                "success": True,
                "raw_response": "评议结果原始响应",
                "result": {
                    "content": "评议结果内容",
                    "scores": {
                        "bias_index": 7.0,
                        "misleading_index": 6.0,
                        "hidden_intent_index": 5.0,
                        "credibility_score": 65.0,
                    },
                },
            }
        )

        # 模拟get_client_for_llm函数
        with patch(
            "acolyte.core.task.processors.review.get_client_for_llm", return_value=mock_client
        ):
            # 执行测试
            result = await processor._single_reviewer_mode(
                task_id, task_content, reviewer, result_ids
            )

            # 验证结果
            assert result["success"] is True
            assert result["task_id"] == task_id
            assert result["final_result_id"] == 5
            assert result["reviewer_id"] == reviewer["id"]

            # 验证方法调用
            processor._get_task_results.assert_called_once_with(task_id, result_ids)
            processor._create_review_prompt.assert_called_once_with(mock_results)
            processor._rebuild_llm_config.assert_called_once_with(reviewer)
            mock_client.process_content.assert_called_once_with(
                content=task_content, prompt="测试评议提示词"
            )
            processor._save_result.assert_called_once_with(
                task_id=task_id,
                llm_id=reviewer["id"],
                result=mock_client.process_content.return_value,
                is_review_result=True,
            )
            processor._update_task_status.assert_called_once_with(task_id, TaskStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_single_reviewer_mode_error(self, processor):
        """测试_single_reviewer_mode方法处理错误的情况"""
        # 准备测试数据
        task_id = 1
        task_content = "测试内容"
        reviewer = {
            "id": 4,
            "name": "Test Reviewer",
            "api_key": "test_api_key",
            "base_url": "https://api.test.com",
            "model_name": "test-model",
            "role": LlmRole.REVIEWER,
            "is_default": False,
        }
        result_ids = [1, 2, 3]

        # 模拟方法
        processor._get_task_results = AsyncMock(return_value=[])
        processor._handle_error = AsyncMock(
            return_value={"success": False, "error": "获取任务结果失败"}
        )

        # 执行测试
        result = await processor._single_reviewer_mode(task_id, task_content, reviewer, result_ids)

        # 验证结果
        assert result["success"] is False
        assert "error" in result
        assert "获取任务结果失败" in result["error"]

        # 验证方法调用
        processor._get_task_results.assert_called_once_with(task_id, result_ids)
        processor._handle_error.assert_called_once_with(task_id, "获取任务结果失败")

    @pytest.mark.asyncio
    async def test_multiple_reviewer_vote_mode(self, processor, mock_results, mock_reviewers):
        """测试_multiple_reviewer_vote_mode方法"""
        # 准备测试数据
        task_id = 1
        task_content = "测试内容"
        result_ids = [1, 2, 3]

        # 模拟方法
        with (
            patch.object(
                processor, "_get_task_results", return_value=mock_results
            ) as mock_get_results,
            patch.object(
                processor, "_create_vote_prompt", return_value="测试投票提示词"
            ) as mock_create_prompt,
            patch.object(processor, "_create_reviewer_task") as mock_create_task,
            patch.object(processor, "_save_votes") as mock_save_votes,
            patch.object(
                processor, "_count_votes", return_value={1: 0, 2: 2, 3: 0}
            ) as mock_count_votes,
            patch.object(processor, "_set_final_result", return_value=True) as mock_set_final,
            patch.object(processor, "_update_task_status", return_value=True) as mock_update_status,
        ):

            # 模拟评议者处理结果
            vote_results = [
                {"success": True, "raw_response": "我投票给 LLM 2 (ID: 2)，因为..."},
                {"success": True, "raw_response": "我投票给 LLM 2 (ID: 2)，因为..."},
            ]

            # 模拟gather_with_concurrency
            with patch(
                "acolyte.core.task.processors.review.gather_with_concurrency",
                return_value=vote_results,
            ):
                # 执行测试
                result = await processor._multiple_reviewer_vote_mode(
                    task_id, task_content, mock_reviewers, result_ids
                )

                # 验证结果
                assert result["success"] is True
                assert result["task_id"] == task_id
                assert result["final_result_id"] == 2
                assert result["vote_counts"] == {1: 0, 2: 2, 3: 0}

                # 验证方法调用
                mock_get_results.assert_awaited_once_with(task_id, result_ids)
                mock_create_prompt.assert_called_once_with(mock_results)
                # 我们不能直接验证调用次数，因为这个方法是在gather_with_concurrency中调用的
                # assert mock_create_task.call_count == 2
                mock_save_votes.assert_awaited_once()
                mock_count_votes.assert_awaited_once_with(task_id, result_ids)
                mock_set_final.assert_awaited_once_with(task_id, 2)
                mock_update_status.assert_awaited_once_with(task_id, TaskStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_multiple_reviewer_vote_mode_error(self, processor, mock_reviewers):
        """测试_multiple_reviewer_vote_mode方法处理错误的情况"""
        # 准备测试数据
        task_id = 1
        task_content = "测试内容"
        result_ids = [1, 2, 3]

        # 模拟方法
        error_result = {"success": False, "error": "获取任务结果失败"}

        with (
            patch.object(processor, "_get_task_results", return_value=[]) as mock_get_results,
            patch.object(
                processor, "_handle_error", return_value=error_result
            ) as mock_handle_error,
        ):

            # 执行测试
            result = await processor._multiple_reviewer_vote_mode(
                task_id, task_content, mock_reviewers, result_ids
            )

            # 验证结果
            assert result["success"] is False
            assert "error" in result
            assert "获取任务结果失败" in result["error"]

            # 验证方法调用
            mock_get_results.assert_awaited_once_with(task_id, result_ids)
            mock_handle_error.assert_awaited_once_with(task_id, "获取任务结果失败")

    @pytest.mark.asyncio
    async def test_create_reviewer_task(self, processor):
        """测试_create_reviewer_task方法"""
        # 准备测试数据
        reviewer = {
            "id": 1,
            "name": "Reviewer 1",
            "api_key": "test_key",
            "base_url": "http://test.com",
            "model_name": "test_model",
        }
        task_content = "测试内容"
        prompt_content = "评议提示词"

        # 模拟_rebuild_llm_config返回LLM配置
        llm_config = MagicMock()
        processor._rebuild_llm_config = MagicMock(return_value=llm_config)

        # 模拟get_client_for_llm返回客户端
        mock_client = AsyncMock()
        process_result = {"success": True, "result": "评议结果"}
        mock_client.process_content = AsyncMock(return_value=process_result)
        with patch(
            "acolyte.core.task.processors.review.get_client_for_llm", return_value=mock_client
        ):
            # 执行测试
            task = await processor._create_reviewer_task(reviewer, task_content, prompt_content)
            result = await task

        # 验证结果
        assert result == process_result

        # 验证方法调用
        processor._rebuild_llm_config.assert_called_once_with(reviewer)
        mock_client.process_content.assert_called_once_with(
            content=task_content, prompt=prompt_content
        )

    @pytest.mark.asyncio
    async def test_create_reviewer_task_error(self, processor):
        """测试_create_reviewer_task方法处理错误的情况"""
        # 准备测试数据
        reviewer = {
            "id": 1,
            "name": "Reviewer 1",
            "api_key": "test_key",
            "base_url": "http://test.com",
            "model_name": "test_model",
        }
        task_content = "测试内容"
        prompt_content = "评议提示词"

        # 模拟_rebuild_llm_config返回LLM配置
        llm_config = MagicMock()
        processor._rebuild_llm_config = MagicMock(return_value=llm_config)

        # 模拟get_client_for_llm返回客户端
        mock_client = AsyncMock()
        mock_client.process_content = AsyncMock(side_effect=Exception("处理失败"))
        with patch(
            "acolyte.core.task.processors.review.get_client_for_llm", return_value=mock_client
        ):
            # 执行测试
            task = await processor._create_reviewer_task(reviewer, task_content, prompt_content)
            with pytest.raises(Exception, match="处理失败"):
                await task

        # 验证方法调用
        processor._rebuild_llm_config.assert_called_once_with(reviewer)
        mock_client.process_content.assert_called_once_with(
            content=task_content, prompt=prompt_content
        )

    def test_rebuild_llm_config(self, processor):
        """测试_rebuild_llm_config方法"""
        # 准备测试数据
        reviewer = {
            "name": "Test Reviewer",
            "api_key": "test_key",
            "base_url": "http://test.com",
            "model_name": "test_model",
            "role": LlmRole.REVIEWER,
        }

        # 执行测试
        result = processor._rebuild_llm_config(reviewer)

        # 验证结果
        assert isinstance(result, LlmConfig)
        assert result.name == reviewer["name"]
        assert result.api_key == reviewer["api_key"]
        assert result.base_url == reviewer["base_url"]
        assert result.model_name == reviewer["model_name"]
        assert result.role == reviewer["role"]

    def test_create_review_prompt(self, processor):
        """测试_create_review_prompt方法"""
        # 准备测试数据
        results = [
            {
                "id": 1,
                "llm_id": 1,
                "raw_response": "LLM 1的分析结果",
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
            },
            {
                "id": 2,
                "llm_id": 2,
                "raw_response": "LLM 2的分析结果",
                "bias_index": 6.8,
                "misleading_index": 5.5,
                "hidden_intent_index": 3.9,
                "credibility_score": 65.2,
            },
        ]

        # 执行测试
        prompt = processor._create_review_prompt(results)

        # 验证结果
        assert isinstance(prompt, str)
        assert "LLM 1" in prompt
        assert "LLM 2" in prompt
        assert "LLM 1的分析结果" in prompt
        assert "LLM 2的分析结果" in prompt

    def test_create_vote_prompt(self, processor):
        """测试_create_vote_prompt方法"""
        # 准备测试数据
        results = [
            {
                "id": 1,
                "llm_id": 1,
                "raw_response": "LLM 1的分析结果",
                "bias_index": 7.5,
                "misleading_index": 6.2,
                "hidden_intent_index": 4.8,
                "credibility_score": 60.5,
            },
            {
                "id": 2,
                "llm_id": 2,
                "raw_response": "LLM 2的分析结果",
                "bias_index": 6.8,
                "misleading_index": 5.5,
                "hidden_intent_index": 3.9,
                "credibility_score": 65.2,
            },
        ]

        # 执行测试
        prompt = processor._create_vote_prompt(results)

        # 验证结果
        assert isinstance(prompt, str)
        assert "LLM 1" in prompt
        assert "LLM 2" in prompt
        assert "LLM 1的分析结果" in prompt
        assert "LLM 2的分析结果" in prompt
        assert "ID: 1" in prompt
        assert "ID: 2" in prompt

    @pytest.mark.asyncio
    async def test_parse_vote_result(self, processor):
        """测试_parse_vote_result方法"""
        # 准备测试数据
        raw_response = "我投票给 LLM 2 (ID: 2)，因为..."
        results = [{"id": 1, "llm_id": 1}, {"id": 2, "llm_id": 2}, {"id": 3, "llm_id": 3}]

        # 执行测试
        result = processor._parse_vote_result(raw_response, results)

        # 验证结果
        assert result == 2

    @pytest.mark.asyncio
    async def test_parse_vote_result_with_no_match(self, processor):
        """测试_parse_vote_result方法处理无匹配的情况"""
        # 准备测试数据
        raw_response = "我投票给 LLM 5 (ID: 5)，因为..."
        results = [{"id": 1, "llm_id": 1}, {"id": 2, "llm_id": 2}, {"id": 3, "llm_id": 3}]

        # 执行测试
        result = processor._parse_vote_result(raw_response, results)

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_count_votes(self, processor):
        """测试_count_votes方法"""
        # 准备测试数据
        task_id = 1
        result_ids = [1, 2, 3]

        # 模拟查询结果
        mock_votes = [
            MagicMock(voted_result_id=2),
            MagicMock(voted_result_id=2),
            MagicMock(voted_result_id=1),
        ]

        # 模拟session
        mock_session = MagicMock()
        mock_session.query().filter_by().all.return_value = mock_votes

        # 模拟run_in_session
        async def mock_run_in_session(func):
            return await func(mock_session)

        with patch(
            "acolyte.core.task.processors.review.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await processor._count_votes(task_id, result_ids)

        # 验证结果
        assert result == {1: 1, 2: 2}  # 只返回有投票的结果ID

    @pytest.mark.asyncio
    async def test_save_votes(self, processor):
        """测试_save_votes方法"""
        # 准备测试数据
        task_id = 1
        reviewer_id = 2
        vote_results = [{"id": 1, "vote": True}, {"id": 2, "vote": False}]

        # 准备投票数据
        votes = [(reviewer_id, {"raw_response": "我投票给 LLM 1 (ID: 1)"})]

        # 模拟session
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        # 模拟run_in_session
        async def mock_run_in_session(func):
            await func(mock_session)
            await mock_session.commit()

        with patch(
            "acolyte.core.task.processors.review.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            await processor._save_votes(task_id, vote_results, votes)

        # 验证方法调用
        assert mock_session.add.call_count == 1  # 只有一个投票被保存
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_final_result(self, processor):
        """测试_set_final_result方法"""
        # 准备测试数据
        task_id = 1
        result_id = 2

        # 模拟session
        mock_task = MagicMock(spec=["final_result_id"])
        mock_session = MagicMock()
        mock_session.query().filter_by().first.return_value = mock_task
        mock_session.commit = AsyncMock()

        # 模拟run_in_session
        async def mock_run_in_session(func):
            result = await func(mock_session)
            await mock_session.commit()
            return result

        with patch(
            "acolyte.core.task.processors.review.run_in_session", side_effect=mock_run_in_session
        ):
            # 执行测试
            result = await processor._set_final_result(task_id, result_id)

        # 验证结果
        assert result is True
        assert mock_task.final_result_id == result_id
        mock_session.commit.assert_awaited_once()
