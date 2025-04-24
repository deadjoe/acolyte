"""
数据库会话管理工具测试

对acolyte.core.db.session模块进行单元测试。
"""

import asyncio
import inspect
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from acolyte.core.db.session import (
    SessionManager,
    extract_model_data,
    run_in_session,
)


class TestSessionScope:
    """测试会话上下文管理器"""

    def test_session_scope_success(self):
        """测试会话上下文管理器的成功路径"""
        # 创建Mock对象
        mock_session = Mock(spec=Session)
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        # 使用会话上下文管理器
        with patch('acolyte.core.db.session.db', mock_db):
            with SessionManager.session_scope() as session:
                # 验证会话
                assert session is mock_session
                # 执行一些操作
                session.query.return_value = "测试查询结果"

            # 验证会话操作
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
            assert not mock_session.rollback.called

    def test_session_scope_with_exception(self):
        """测试会话上下文管理器在异常情况下的行为"""
        # 创建Mock对象
        mock_session = Mock(spec=Session)
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        # 使用会话上下文管理器
        with patch('acolyte.core.db.session.db', mock_db):
            with pytest.raises(SQLAlchemyError):
                with SessionManager.session_scope() as session:
                    # 抛出异常
                    raise SQLAlchemyError("数据库操作失败")

            # 验证会话操作
            assert not mock_session.commit.called
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


class TestWithSession:
    """测试会话管理装饰器"""

    def test_with_session_decorator(self):
        """测试同步函数的会话管理装饰器"""
        # 创建Mock对象
        mock_session = Mock(spec=Session)
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        # 创建被装饰的函数
        @SessionManager.with_session
        def test_func(session, a, b=2):
            assert session is mock_session
            return a + b

        # 使用装饰器
        with patch('acolyte.core.db.session.db', mock_db):
            result = test_func(3, b=4)

        # 验证结果和会话操作
        assert result == 7
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


class TestAsyncWithSession:
    """测试异步会话管理装饰器"""

    @pytest.mark.asyncio
    async def test_async_with_session_for_coroutine(self):
        """测试协程函数的异步会话管理装饰器"""
        # 创建Mock对象
        mock_session = Mock(spec=Session)
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        # 创建被装饰的异步函数
        @SessionManager.async_with_session
        async def test_async_func(session, a, b=2):
            assert session is mock_session
            return a * b

        # 使用装饰器
        with patch('acolyte.core.db.session.db', mock_db):
            result = await test_async_func(5, b=6)

        # 验证结果和会话操作
        assert result == 30
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_with_session_for_sync_func(self):
        """测试同步函数的异步会话管理装饰器"""
        # 创建Mock对象
        mock_session = Mock(spec=Session)
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        # 创建被装饰的同步函数
        @SessionManager.async_with_session
        def test_sync_func(session, a, b=2):
            assert session is mock_session
            return a - b

        # 使用装饰器
        with patch('acolyte.core.db.session.db', mock_db):
            result = await test_sync_func(10, b=3)

        # 验证结果和会话操作
        assert result == 7
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


class TestSafeDetach:
    """测试安全分离数据库对象功能"""

    def test_safe_detach_none(self):
        """测试对None对象的安全分离"""
        result = SessionManager.safe_detach(None)
        assert result == {}

    def test_safe_detach_with_to_dict(self):
        """测试带有to_dict方法的对象的安全分离"""
        # 创建带to_dict方法的模拟对象
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {"id": 1, "name": "test"}

        # 测试安全分离
        result = SessionManager.safe_detach(mock_obj)

        # 验证结果
        assert result == {"id": 1, "name": "test"}
        mock_obj.to_dict.assert_called_once()

    def test_safe_detach_with_dict(self):
        """测试带有__dict__属性的对象的安全分离"""
        # 创建带属性的模拟对象
        class MockModel:
            def __init__(self):
                self.id = 2
                self.name = "test_model"
                self._private = "private_value"

        mock_obj = MockModel()

        # 测试安全分离
        result = SessionManager.safe_detach(mock_obj)

        # 验证结果
        assert result == {"id": 2, "name": "test_model"}
        assert "_private" not in result


class TestGetEntityById:
    """测试根据ID获取实体功能"""

    def test_get_entity_by_id_with_existing_session(self):
        """测试使用已存在的会话获取实体"""
        # 创建模拟会话和模型类
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = "模拟实体对象"

        mock_model = Mock()

        # 测试获取实体
        result = SessionManager.get_entity_by_id(mock_model, 123, mock_session)

        # 验证结果和调用
        assert result == "模拟实体对象"
        mock_session.query.assert_called_once_with(mock_model)
        mock_query.filter_by.assert_called_once_with(id=123)
        mock_filter.first.assert_called_once()
        # 不应关闭传入的会话
        assert not mock_session.close.called

    def test_get_entity_by_id_without_session(self):
        """测试在没有提供会话的情况下获取实体"""
        # 创建模拟数据库和会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_filter
        mock_filter.first.return_value = "模拟实体对象"

        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        mock_model = Mock()

        # 测试获取实体
        with patch('acolyte.core.db.session.db', mock_db):
            result = SessionManager.get_entity_by_id(mock_model, 456)

        # 验证结果和调用
        assert result == "模拟实体对象"
        mock_db.get_session.assert_called_once()
        mock_session.query.assert_called_once_with(mock_model)
        mock_query.filter_by.assert_called_once_with(id=456)
        mock_filter.first.assert_called_once()
        # 应该关闭新创建的会话
        mock_session.close.assert_called_once()

    def test_get_entity_by_id_with_exception(self):
        """测试在查询过程中发生异常的情况"""
        # 创建模拟数据库和会话
        mock_session = Mock(spec=Session)
        mock_session.query.side_effect = SQLAlchemyError("查询失败")

        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        mock_model = Mock()

        # 测试获取实体
        with patch('acolyte.core.db.session.db', mock_db):
            with patch('acolyte.core.db.session.logger') as mock_logger:
                result = SessionManager.get_entity_by_id(mock_model, 789)

                # 验证日志记录
                mock_logger.error.assert_called_once()

        # 验证结果和调用
        assert result is None
        mock_db.get_session.assert_called_once()
        mock_session.query.assert_called_once_with(mock_model)
        # 应该关闭会话，即使发生异常
        mock_session.close.assert_called_once()


class TestExtractModelData:
    """测试提取模型数据功能"""

    def test_extract_model_data_none(self):
        """测试提取空对象的数据"""
        with patch('acolyte.core.db.session.logger') as mock_logger:
            result = extract_model_data(None)

            # 验证日志记录
            mock_logger.warning.assert_called_once_with("无法提取空对象数据")

        # 验证结果
        assert result == {}

    def test_extract_model_data_with_to_dict(self):
        """测试提取带有to_dict方法的对象数据"""
        # 创建带to_dict方法的模拟对象
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {"id": 1, "name": "test_model"}

        # 测试提取数据，不包含关系
        result = extract_model_data(mock_obj, include_relationships=False)

        # 验证结果
        assert result == {"id": 1, "name": "test_model"}
        mock_obj.to_dict.assert_called_once()

    def test_extract_model_data_with_to_dict_and_relationships(self):
        """测试提取带有to_dict方法和关系参数的对象数据"""
        # 创建带to_dict方法和include_relationships参数的模拟对象
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {"id": 1, "name": "test_model", "related": {"id": 2}}

        # 模拟函数签名
        mock_signature = Mock()
        mock_signature.parameters = {"include_relationships": None}

        # 测试提取数据，包含关系
        with patch('inspect.signature', return_value=mock_signature):
            result = extract_model_data(mock_obj, include_relationships=True)

        # 验证结果
        assert result == {"id": 1, "name": "test_model", "related": {"id": 2}}
        mock_obj.to_dict.assert_called_once_with(include_relationships=True)

    def test_extract_model_data_manual(self):
        """测试手动提取对象数据"""
        # 创建带属性的模拟对象
        class MockModel:
            def __init__(self):
                self.__dict__ = {
                    "id": 3,
                    "name": "manual_model",
                    "_private": "private_value",
                    "created_at": Mock(isoformat=lambda: "2025-04-25T00:00:00")
                }

        mock_obj = MockModel()

        # 测试提取数据
        result = extract_model_data(mock_obj)

        # 验证结果
        assert result["id"] == 3
        assert result["name"] == "manual_model"
        assert "_private" not in result
        assert result["created_at"] == "2025-04-25T00:00:00"

    def test_extract_model_data_with_exception(self):
        """测试提取数据时发生异常的情况"""
        # 创建一个在访问__dict__时会抛出异常的对象
        class ExceptionModel:
            @property
            def __dict__(self):
                raise Exception("字典访问错误")
                
        mock_obj = ExceptionModel()
        
        # 测试提取数据
        with patch('acolyte.core.db.session.logger') as mock_logger:
            result = extract_model_data(mock_obj)
            
            # 验证日志记录
            mock_logger.error.assert_called_once()
            
        # 验证结果
        assert result == {}

    def test_extract_model_data_with_relationships(self):
        """测试提取带关系的对象数据"""
        # 创建复杂的模拟对象结构
        class MockRelated:
            def __init__(self):
                self.__dict__ = {"id": 101, "name": "related_model"}

        class MockRelationship:
            def __init__(self):
                self.prop = True  # 模拟SQLAlchemy关系属性

        class MockModel:
            def __init__(self):
                self.__dict__ = {"id": 100, "name": "parent_model"}
                self.related_single = MockRelated()
                self.related_list = [MockRelated(), MockRelated()]

            @classmethod
            def get_relationship(cls):
                return [
                    ("related_single", MockRelationship()),
                    ("related_list", MockRelationship())
                ]

        mock_obj = MockModel()

        # 模拟inspect.getmembers以返回关系
        with patch('inspect.getmembers', return_value=MockModel.get_relationship()):
            # 测试提取数据，包含关系
            result = extract_model_data(mock_obj, include_relationships=True)

        # 验证结果
        assert result["id"] == 100
        assert result["name"] == "parent_model"
        assert "related_single" in result
        assert result["related_single"]["id"] == 101
        assert "related_list" in result
        assert isinstance(result["related_list"], list)
        assert len(result["related_list"]) == 2
        assert result["related_list"][0]["id"] == 101


@pytest.mark.asyncio
class TestRunInSession:
    """测试在会话中运行函数功能"""

    async def test_run_in_session_with_async_func(self):
        """测试在会话中运行异步函数"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        # 创建异步测试函数
        async def test_async_func(session, a, b=2):
            assert session is mock_session
            return a * b

        # 测试在会话中运行函数
        with patch('acolyte.core.db.session.db', mock_db):
            result = await run_in_session(test_async_func, 5, b=6)

        # 验证结果
        assert result == 30

    async def test_run_in_session_with_sync_func(self):
        """测试在会话中运行同步函数"""
        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_db = Mock()
        mock_db.get_session.return_value = mock_session

        # 创建同步测试函数
        def test_sync_func(session, a, b=2):
            assert session is mock_session
            return a - b

        # 测试在会话中运行函数
        with patch('acolyte.core.db.session.db', mock_db):
            result = await run_in_session(test_sync_func, 10, b=3)

        # 验证结果
        assert result == 7
