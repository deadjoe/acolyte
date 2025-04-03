"""
数据库管理工具
"""
import os
import traceback
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from acolyte.core.db.models import Base
from acolyte.utils.logging import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


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
        logger.info(f"初始化数据库连接: {self.db_url}")
        self.engine = create_engine(self.db_url)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        logger.debug("数据库会话工厂已创建")

    def create_tables(self):
        """创建所有表"""
        logger.info("创建数据库表")
        Base.metadata.create_all(self.engine)
        logger.debug("数据库表创建完成")

    def drop_tables(self):
        """删除所有表"""
        logger.warning("删除所有数据库表")
        Base.metadata.drop_all(self.engine)
        logger.debug("数据库表删除完成")

    def get_session(self):
        """获取一个新的会话

        Returns:
            新创建的数据库会话
        """
        session = self.Session()
        logger.debug("创建新的数据库会话")
        return session

    @contextmanager
    def session_scope(self):
        """提供事务范围的会话上下文管理器

        使用示例:
            with db.session_scope() as session:
                session.add(some_object)
                # 无需手动commit，退出上下文时自动提交
                # 如有异常自动回滚
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
            logger.debug("会话提交成功")
        except Exception as e:
            logger.error(f"会话执行异常，回滚事务: {str(e)}")
            logger.debug(f"异常详情: {traceback.format_exc()}")
            session.rollback()
            raise
        finally:
            session.close()
            logger.debug("会话已关闭")


# 默认数据库实例
db = Database()