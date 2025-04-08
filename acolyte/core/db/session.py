"""
会话管理工具

提供SQLAlchemy会话管理的辅助工具，重点解决异步操作中的会话管理问题。
"""

import functools
import inspect
from contextlib import contextmanager
from typing import Any, Dict, Optional, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from acolyte.core.db.database import db
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 定义类型变量
T = TypeVar("T")
R = TypeVar("R")


class SessionManager:
    """
    会话管理器类

    该类提供会话管理的辅助方法，简化数据库操作和异常处理。
    它封装了SQLAlchemy会话的创建、提交和回滚操作，并提供了上下文管理器和装饰器。

    主要功能：
    - 会话上下文管理：自动创建、提交和回滚会话
    - 会话装饰器：为同步和异步函数提供会话管理
    - 安全分离对象：将数据库对象从会话中分离，防止过期会话问题
    - 实体查询帮助器：简化实体的查询和获取

    与异步编程的兼容性：
    - 提供了异步会话装饰器，支持异步函数中的数据库操作
    - 提供了run_in_session函数，在异步上下文中运行数据库操作
    """

    @staticmethod
    @contextmanager
    def session_scope():
        """
        会话上下文管理器

        使用with语句创建数据库会话，自动处理提交、回滚和关闭。
        相比原始db.session_scope，增强了日志记录和错误处理。

        用法:
            with SessionManager.session_scope() as session:
                # 使用session进行数据库操作
        """
        session = None
        try:
            session = db.get_session()
            logger.debug("数据库会话已创建")
            yield session
            session.commit()
            logger.debug("数据库会话已提交")
        except SQLAlchemyError as e:
            logger.error(f"数据库操作失败: {str(e)}", exc_info=True)
            if session:
                session.rollback()
                logger.debug("数据库会话已回滚")
            raise
        finally:
            if session:
                session.close()
                logger.debug("数据库会话已关闭")

    @staticmethod
    def with_session(func):
        """
        会话管理装饰器

        自动为函数创建会话并传入，处理会话的生命周期。
        适用于同步函数。

        用法:
            @SessionManager.with_session
            def get_item(session, item_id):
                return session.query(Item).get(item_id)
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with SessionManager.session_scope() as session:
                return func(session, *args, **kwargs)

        return wrapper

    @staticmethod
    def async_with_session(func):
        """
        异步会话管理装饰器

        自动为异步函数创建会话并传入，处理会话的生命周期。

        用法:
            @SessionManager.async_with_session
            async def get_item_async(session, item_id):
                return session.query(Item).get(item_id)
        """

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with SessionManager.session_scope() as session:
                if inspect.iscoroutinefunction(func):
                    return await func(session, *args, **kwargs)
                return func(session, *args, **kwargs)

        return wrapper

    @staticmethod
    def safe_detach(obj: Any) -> Dict[str, Any]:
        """
        安全分离数据库对象

        该方法将SQLAlchemy对象转换为字典，避免会话关闭后的访问问题。
        它解决了“已分离实例”和“过期会话”等常见问题，使得可以在会话关闭后仍然安全地访问对象数据。

        分离过程：
        1. 检查对象是否为None，如果是则返回None
        2. 将对象转换为字典，包含所有非下划线开头的属性
        3. 如果对象有__dict__属性，则使用它作为基础
        4. 如果对象没有__dict__属性，则尝试使用dir()获取属性
        5. 过滤掉方法、特殊属性和下划线开头的属性

        Args:
            obj: 要分离的数据库对象，通常是SQLAlchemy模型实例

        Returns:
            Dict[str, Any]: 包含对象属性的字典，键为属性名，值为属性值
        """
        if obj is None:
            return {}

        # 如果对象有to_dict方法，优先使用
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()

        # 否则手动提取属性
        result = {}
        for key in obj.__dict__:
            if not key.startswith("_"):
                result[key] = getattr(obj, key)
        return result

    @staticmethod
    def get_entity_by_id(
        model_class: Any, entity_id: int, session: Optional[Session] = None
    ) -> Optional[Any]:
        """
        根据ID获取实体

        该方法安全地根据ID获取数据库实体，并自动处理会话管理。
        它提供了一种简单的方式来查询实体，而不需要手动创建和管理会话。

        查询流程：
        1. 如果没有提供会话，则创建新的会话
        2. 使用模型类和ID查询实体
        3. 如果创建了新会话，则在操作完成后关闭它
        4. 如果发生异常，则记录错误并返回None

        Args:
            model_class: 要查询的模型类，如User、LlmConfig等
            entity_id: 要查询的实体ID
            session: 可选的会话对象，如果不提供则创建新会话

        Returns:
            Optional[Any]: 找到的实体对象，如果未找到或发生错误则返回None
        """
        close_session = False
        if session is None:
            session = db.get_session()
            close_session = True

        try:
            return session.query(model_class).filter_by(id=entity_id).first()
        except SQLAlchemyError as e:
            logger.error(f"获取实体失败: {str(e)}", exc_info=True)
            return None
        finally:
            if close_session and session:
                session.close()


def extract_model_data(model_obj: Any, include_relationships: bool = False) -> Dict[str, Any]:
    """
    提取模型数据

    将SQLAlchemy模型对象转换为字典，避免会话关闭后的访问问题。
    比safe_detach更全面，支持关系处理。

    Args:
        model_obj: 模型对象
        include_relationships: 是否包含关系属性

    Returns:
        包含对象数据的字典
    """
    # 添加详细日志
    model_type = type(model_obj).__name__ if model_obj else "None"
    logger.debug(f"提取模型数据: 类型={model_type}, 包含关系={include_relationships}")

    if model_obj is None:
        logger.warning("无法提取空对象数据")
        return {}

    # 如果对象有to_dict方法，优先使用
    if hasattr(model_obj, "to_dict") and callable(model_obj.to_dict):
        if "include_relationships" in inspect.signature(model_obj.to_dict).parameters:
            return model_obj.to_dict(include_relationships=include_relationships)
        return model_obj.to_dict()

    # 手动提取属性
    result = {}
    try:
        # 获取对象的字典副本，避免直接访问可能引发懒加载的属性
        obj_dict = model_obj.__dict__.copy()
        for key in obj_dict:
            if not key.startswith("_"):
                try:
                    value = obj_dict[key]
                    # 处理日期时间类型
                    if hasattr(value, "isoformat"):
                        result[key] = value.isoformat()
                    else:
                        result[key] = value
                except (AttributeError, KeyError) as e:
                    logger.warning(f"提取属性 {key} 失败: {str(e)}")
                    # 跳过此属性
    except Exception as e:
        logger.error(f"提取对象数据时出错: {str(e)}", exc_info=True)

    # 处理关系属性
    if include_relationships:
        for relationship in inspect.getmembers(
            model_obj.__class__,
            lambda attr: hasattr(attr, "prop") if hasattr(attr, "prop") else False,
        ):
            if hasattr(model_obj, relationship[0]):
                rel_obj = getattr(model_obj, relationship[0])
                if rel_obj is not None:
                    if isinstance(rel_obj, list):
                        result[relationship[0]] = [
                            extract_model_data(item, False) for item in rel_obj
                        ]
                    else:
                        result[relationship[0]] = extract_model_data(rel_obj, False)

    return result


async def run_in_session(func, *args, **kwargs):
    """
    在会话中运行函数

    该函数是为异步环境提供的辅助函数，确保函数在数据库会话中执行。
    它可以同时处理同步函数和异步函数，自动检测函数类型并适当地调用。

    这个函数在异步上下文中特别有用，例如在FastAPI路由处理程序中或其他异步任务中。

    执行流程：
    1. 创建一个数据库会话
    2. 检查函数是否是协程函数（异步函数）
    3. 如果是异步函数，使用await调用它
    4. 如果是同步函数，直接调用它
    5. 会话在函数执行完成后自动关闭

    Args:
        func: 要在会话中执行的函数，可以是同步函数或异步函数
        *args: 传递给函数的位置参数
        **kwargs: 传递给函数的关键字参数

    Returns:
        Any: 函数的执行结果

    Note:
        函数的第一个参数必须是会话对象，因为会话将作为第一个参数传递给函数。
    """
    with SessionManager.session_scope() as session:
        if inspect.iscoroutinefunction(func):
            return await func(session, *args, **kwargs)
        return func(session, *args, **kwargs)
