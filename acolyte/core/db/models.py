"""
数据库模型定义
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

# 多对多关系表：任务与LLM
task_llm_association = Table(
    "task_llm_association",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id"), primary_key=True),
    Column("llm_id", Integer, ForeignKey("llm_configs.id"), primary_key=True),
    Column("is_reviewer", Boolean, default=False),
)


class LlmRole(enum.Enum):
    """
    LLM角色枚举

    定义了LLM可以担任的不同角色，用于在不同的处理模式中区分LLM的功能。

    成员：
        NORMAL: 普通评估者角色，用于分析内容并生成评估结果
        REVIEWER: 评议者角色，用于对多个普通评估者的结果进行评估和投票
    """

    NORMAL = "normal"  # 普通评估者
    REVIEWER = "reviewer"  # 评议者


class ProcessingMode(enum.Enum):
    """
    处理模式枚举

    定义了系统支持的不同任务处理模式，用于控制任务的执行方式。
    每种模式对应不同的任务处理器实现。

    成员：
        SINGLE: 单LLM处理模式，使用单个LLM处理任务，通常是默认的LLM
        MULTIPLE: 多LLM处理模式，使用多个LLM并行处理任务，返回所有结果
        MULTIPLE_WITH_REVIEW: 多LLM带评议模式，使用多个LLM处理任务，然后由评议者LLM进行评估和投票
    """

    SINGLE = "single"  # 单LLM处理
    MULTIPLE = "multiple"  # 多LLM处理
    MULTIPLE_WITH_REVIEW = "multiple_with_review"  # 多LLM带评议


class TaskStatus(enum.Enum):
    """
    任务状态枚举

    定义了任务在处理生命周期中的不同状态。
    这些状态用于跟踪任务的进度和结果。

    成员：
        PENDING: 等待处理状态，任务创建后的初始状态
        PROCESSING: 处理中状态，任务正在被LLM处理
        COMPLETED: 已完成状态，任务处理成功并有结果
        FAILED: 失败状态，任务处理过程中出现错误
    """

    PENDING = "pending"  # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


class LlmConfig(Base):
    """
    LLM配置模型

    该模型存储LLM的配置信息，包括API密钥、基础URL、模型名称等。
    每个LlmConfig对象代表一个可用的LLM配置，可以被任务引用。

    字段：
        id: 主键，自增整数
        name: LLM名称，必填且唯一
        description: LLM描述，可选
        api_key: API密钥，必填
        base_url: API基础URL，必填
        model_name: 模型名称，必填
        role: LLM角色，默认为普通评估者
        is_default: 是否为默认LLM，默认为否
        created_at: 创建时间
        updated_at: 更新时间

    关系：
        task_results: 与任务结果的一对多关系
        tasks: 与任务的多对多关系，通过task_llm_association表
    """

    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    api_key = Column(String(255), nullable=False)
    base_url = Column(String(255), nullable=False)
    model_name = Column(String(100), nullable=False)
    role = Column(Enum(LlmRole), default=LlmRole.NORMAL)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    task_results = relationship("TaskResult", back_populates="llm_config")
    tasks = relationship("Task", secondary=task_llm_association, back_populates="llm_configs")
    reviewer_votes = relationship("ReviewerVote", back_populates="reviewer")

    def to_dict(self):
        """转换为字典，不包含关系和日期"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model_name": self.model_name,
            "role": self.role.value,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Prompt(Base):
    """Prompt模板模型"""

    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    version = Column(String(50), nullable=False)
    model_target = Column(String(50))
    content = Column(Text, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    file_path = Column(String(255))  # 对应文件系统的路径
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    tasks = relationship("Task", back_populates="prompt")

    def to_dict(self, include_content=False):
        """转换为字典，不包含关系和日期"""
        result = {
            "id": self.id,
            "version": self.version,
            "model_target": self.model_target,
            "description": self.description,
            "is_active": self.is_active,
            "file_path": self.file_path,  # 总是包含文件路径
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            result["content"] = self.content
        return result


class TaskResult(Base):
    """任务结果模型"""

    __tablename__ = "task_results"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    llm_id = Column(Integer, ForeignKey("llm_configs.id"), nullable=False)
    raw_response = Column(Text)  # 原始响应
    processed_result = Column(Text)  # 处理后的结果
    bias_index = Column(Float)  # 偏见指数
    misleading_index = Column(Float)  # 误导性指数
    hidden_intent_index = Column(Float)  # 隐藏意图指数
    credibility_score = Column(Float)  # 可信度分数
    is_review_result = Column(Boolean, default=False)  # 是否是评议结果
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系 - 延迟定义Task关联
    llm_config = relationship("LlmConfig", back_populates="task_results")
    votes = relationship("ReviewerVote", back_populates="voted_result")

    def to_dict(self, include_raw_response=False):
        """转换为字典，不包含关系和日期"""
        result = {
            "id": self.id,
            "task_id": self.task_id,
            "llm_id": self.llm_id,
            "bias_index": self.bias_index,
            "misleading_index": self.misleading_index,
            "hidden_intent_index": self.hidden_intent_index,
            "credibility_score": self.credibility_score,
            "is_review_result": self.is_review_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_raw_response:
            result["raw_response"] = self.raw_response
        return result


class Task(Base):
    """任务模型"""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    processing_mode = Column(Enum(ProcessingMode), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    prompt_id = Column(Integer, ForeignKey("prompts.id"))
    final_result_id = Column(Integer, ForeignKey("task_results.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    prompt = relationship("Prompt", back_populates="tasks")
    results = relationship("TaskResult", foreign_keys="TaskResult.task_id", back_populates="task")
    final_result = relationship("TaskResult", foreign_keys=[final_result_id])
    llm_configs = relationship("LlmConfig", secondary=task_llm_association, back_populates="tasks")
    reviewer_votes = relationship("ReviewerVote", back_populates="task")

    def to_dict(self, include_content=True):
        """转换为字典，不包含关系和日期"""
        result = {
            "id": self.id,
            "processing_mode": self.processing_mode.value,
            "status": self.status.value,
            "prompt_id": self.prompt_id,
            "final_result_id": self.final_result_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_content:
            result["content"] = self.content
        return result


# 添加延迟定义的Task关系到TaskResult
TaskResult.task = relationship("Task", foreign_keys=[TaskResult.task_id], back_populates="results")


class ReviewerVote(Base):
    """评议者投票模型"""

    __tablename__ = "reviewer_votes"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("llm_configs.id"), nullable=False)
    voted_result_id = Column(Integer, ForeignKey("task_results.id"), nullable=False)
    comment = Column(Text)  # 评议者评论
    raw_response = Column(Text)  # 原始响应
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    task = relationship("Task", back_populates="reviewer_votes")
    reviewer = relationship("LlmConfig", back_populates="reviewer_votes")
    voted_result = relationship("TaskResult", back_populates="votes")

    def to_dict(self, include_raw_response=False):
        """转换为字典格式"""
        result = {
            "id": self.id,
            "task_id": self.task_id,
            "reviewer_id": self.reviewer_id,
            "voted_result_id": self.voted_result_id,
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_raw_response:
            result["raw_response"] = self.raw_response
        return result


# 数据库连接和会话
def get_engine(db_url="sqlite:///acolyte.db"):
    return create_engine(db_url)


def get_session_maker(engine):
    return sessionmaker(bind=engine)


def init_db(engine):
    """初始化数据库"""
    Base.metadata.create_all(engine)
