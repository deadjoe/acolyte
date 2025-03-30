"""
数据库管理工具
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from acolyte.core.db.models import Base


class Database:
    """数据库管理类"""

    def __init__(self, db_url=None):
        """初始化数据库连接

        Args:
            db_url: 数据库连接URL，默认为配置文件中的URL或SQLite本地文件
        """
        self.db_url = db_url or os.environ.get(
            "ACOLYTE_DB_URL", "sqlite:///acolyte.db"
        )
        self.engine = create_engine(self.db_url)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        """删除所有表"""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session_scope(self):
        """提供事务范围的会话上下文管理器

        使用示例:
            with db.session_scope() as session:
                session.add(some_object)
                # 无需手动commit，退出上下文时自动提交
                # 如有异常自动回滚
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# 默认数据库实例
db = Database()