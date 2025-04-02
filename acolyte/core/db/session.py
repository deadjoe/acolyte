"""
会话管理工具

提供SQLAlchemy会话管理的辅助工具，重点解决异步操作中的会话管理问题。
"""
import functools
import inspect
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from acolyte.core.db.database import db
from acolyte.utils.logging import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 定义类型变量
T = TypeVar('T')
R = TypeVar('R')


class SessionManager:
    """
    会话管理器类
    
    提供会话管理的辅助方法，简化数据库操作和异常处理。
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
        
        将SQLAlchemy对象转换为字典，避免会话关闭后的访问问题。
        
        Args:
            obj: 数据库对象
            
        Returns:
            包含对象属性的字典
        """
        if obj is None:
            return {}
            
        # 如果对象有to_dict方法，优先使用
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()
            
        # 否则手动提取属性
        result = {}
        for key in obj.__dict__:
            if not key.startswith('_'):
                result[key] = getattr(obj, key)
        return result
    
    @staticmethod
    def get_entity_by_id(model_class: Any, entity_id: int, session: Optional[Session] = None) -> Optional[Any]:
        """
        根据ID获取实体
        
        安全地根据ID获取数据库实体，处理会话管理。
        
        Args:
            model_class: 模型类
            entity_id: 实体ID
            session: 可选的会话对象，如果不提供则创建新会话
            
        Returns:
            找到的实体对象，或None
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
    if model_obj is None:
        return {}
        
    # 如果对象有to_dict方法，优先使用
    if hasattr(model_obj, 'to_dict') and callable(getattr(model_obj, 'to_dict')):
        if 'include_relationships' in inspect.signature(model_obj.to_dict).parameters:
            return model_obj.to_dict(include_relationships=include_relationships)
        return model_obj.to_dict()
        
    # 手动提取属性
    result = {}
    for key in model_obj.__dict__:
        if not key.startswith('_'):
            value = getattr(model_obj, key)
            # 处理日期时间类型
            if hasattr(value, 'isoformat'):
                result[key] = value.isoformat()
            else:
                result[key] = value
                
    # 处理关系属性
    if include_relationships:
        for relationship in inspect.getmembers(
            model_obj.__class__, 
            lambda attr: hasattr(attr, 'prop') if hasattr(attr, 'prop') else False
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
    
    为异步环境提供的辅助函数，确保函数在会话中执行。
    
    Args:
        func: 要执行的函数
        args: 位置参数
        kwargs: 关键字参数
        
    Returns:
        函数执行结果
    """
    with SessionManager.session_scope() as session:
        if inspect.iscoroutinefunction(func):
            return await func(session, *args, **kwargs)
        return func(session, *args, **kwargs)