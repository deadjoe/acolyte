"""Pytest配置文件"""

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import clear_mappers, sessionmaker

# 确保可以导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acolyte.core.db.models import Base


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
