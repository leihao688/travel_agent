import sys
import os

# 添加项目根目录到 sys.path，解决模块导入问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from utils.config_load import mysql_config
from utils.logger_tool import LogConfig
from typing import Optional

log = LogConfig()
logger = log.get_logger(__name__)

Base = declarative_base()


class ParentChunk(Base):
    """父块表 - 存储完整的Markdown语义块"""
    __tablename__ = 'parent_chunks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_id = Column(String(128), unique=True, nullable=False, index=True, comment='父块唯一ID')
    file_path = Column(String(512), nullable=False, comment='源文件路径')
    file_name = Column(String(256), nullable=False, index=True, comment='源文件名')
    file_md5 = Column(String(64), nullable=True, comment='文件MD5值')

    # Markdown结构信息
    header_1 = Column(String(512), nullable=True, comment='一级标题')
    header_2 = Column(String(512), nullable=True, comment='二级标题')
    header_3 = Column(String(512), nullable=True, comment='三级标题')

    # 完整内容
    full_content = Column(Text, nullable=False, comment='父块完整原始内容')

    # 内容统计
    content_length = Column(Integer, nullable=False, default=0, comment='原始内容长度')
    child_count = Column(Integer, nullable=False, default=1, comment='子块数量')

    # 元数据
    metadata_json = Column(Text, nullable=True, comment='额外元数据JSON')
    chunk_index = Column(Integer, nullable=False, comment='在文件中的顺序索引')

    # ChromaDB关联
    chroma_collection = Column(String(128), default='agent', comment='ChromaDB集合名称')

    # 时间戳
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='创建时间')
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), comment='更新时间')

    __table_args__ = (
        Index('idx_file_header', 'file_name', 'header_1', 'header_2'),
        {'comment': 'RAG父块存储表'}
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'chunk_id': self.chunk_id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_md5': self.file_md5,
            'header_1': self.header_1,
            'header_2': self.header_2,
            'header_3': self.header_3,
            'full_content': self.full_content,
            'content_length': self.content_length,
            'child_count': self.child_count,
            'metadata_json': self.metadata_json,
            'chunk_index': self.chunk_index,
            'chroma_collection': self.chroma_collection,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class FileProcessingLog(Base):
    """文件处理日志表"""
    __tablename__ = 'file_processing_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(256), nullable=False, comment='文件名')
    file_path = Column(String(512), nullable=False, comment='文件路径')
    file_md5 = Column(String(64), nullable=False, unique=True, comment='文件MD5')

    total_parent_chunks = Column(Integer, default=0, comment='生成的父块数量')
    total_child_chunks = Column(Integer, default=0, comment='生成的子块数量')

    processing_status = Column(
        Enum('pending', 'processing', 'completed', 'failed'),
        default='pending',
        comment='处理状态'
    )
    error_message = Column(Text, comment='错误信息')

    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment='处理时间')


class ParentChunkStore:
    """
    MySQL数据库管理器 - 用于存储父块元数据

    职责：
    - 管理父块的持久化存储
    - 提供CRUD操作接口
    - 支持批量操作和事务管理
    """

    def __init__(self):
        config = mysql_config
        db_config = config.get('database', {})

        self.database_url = (
            f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            f"?charset=utf8mb4"
        )

        self.engine = create_engine(
            self.database_url,
            pool_size=db_config.get('pool_size', 5),
            max_overflow=db_config.get('max_overflow', 10),
            echo=db_config.get('echo', False)
        )

        SessionLocal = sessionmaker(bind=self.engine)
        self.SessionLocal = SessionLocal

        # 创建表
        Base.metadata.create_all(bind=self.engine)
        logger.info("MySQL数据库表初始化完成")

    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()

    def add_parent_chunk(self, chunk_data: dict) -> str:
        """添加单个父块记录"""
        session = self.get_session()
        try:
            parent_chunk = ParentChunk(**chunk_data)
            session.add(parent_chunk)
            session.commit()
            logger.debug(f"父块已保存: {parent_chunk.chunk_id}")
            return parent_chunk.chunk_id
        except Exception as e:
            session.rollback()
            logger.error(f"保存父块失败: {str(e)}")
            raise e
        finally:
            session.close()

    def batch_add_parent_chunks(self, chunks_data: list) -> int:
        """批量添加父块记录"""
        if not chunks_data:
            return 0

        session = self.get_session()
        try:
            parent_chunks = [ParentChunk(**data) for data in chunks_data]
            session.add_all(parent_chunks)
            session.commit()
            logger.info(f"批量保存父块完成: {len(parent_chunks)}条")
            return len(parent_chunks)
        except Exception as e:
            session.rollback()
            logger.error(f"批量保存父块失败: {str(e)}")
            raise e
        finally:
            session.close()

    def get_parent_by_id(self, chunk_id: str) -> Optional[dict]:
        """根据ID获取父块"""
        session = self.get_session()
        try:
            parent = session.query(ParentChunk).filter(
                ParentChunk.chunk_id == chunk_id
            ).first()
            return parent.to_dict() if parent else None
        finally:
            session.close()

    def get_parents_by_ids(self, chunk_ids: list) -> list:
        """批量获取父块（RRF重排序后召回）"""
        if not chunk_ids:
            return []

        session = self.get_session()
        try:
            parents = session.query(ParentChunk).filter(
                ParentChunk.chunk_id.in_(chunk_ids)
            ).all()
            return [parent.to_dict() for parent in parents]
        finally:
            session.close()

    def get_parents_by_file(self, file_name: str) -> list:
        """根据文件名获取所有父块"""
        session = self.get_session()
        try:
            parents = session.query(ParentChunk).filter(
                ParentChunk.file_name == file_name
            ).order_by(ParentChunk.chunk_index).all()
            return [parent.to_dict() for parent in parents]
        finally:
            session.close()

    def search_parents_by_header(self, header_1: Optional[str] = None, header_2: Optional[str] = None) -> list:
        """根据标题搜索父块"""
        session = self.get_session()
        try:
            query = session.query(ParentChunk)
            if header_1:
                query = query.filter(ParentChunk.header_1.like(f'%{header_1}%'))
            if header_2:
                query = query.filter(ParentChunk.header_2.like(f'%{header_2}%'))
            parents = query.all()
            return [parent.to_dict() for parent in parents]
        finally:
            session.close()

    def delete_by_file(self, file_name: str) -> int:
        """删除文件相关的所有父块"""
        session = self.get_session()
        try:
            count = session.query(ParentChunk).filter(
                ParentChunk.file_name == file_name
            ).delete()
            session.commit()
            logger.info(f"删除文件父块: {file_name}, 共{count}条")
            return count
        except Exception as e:
            session.rollback()
            logger.error(f"删除父块失败: {str(e)}")
            raise e
        finally:
            session.close()

    def add_processing_log(self, log_data: dict) -> None:
        """添加或更新文件处理日志"""
        session = self.get_session()
        try:
            file_md5 = log_data.get('file_md5')
            if not file_md5:
                raise ValueError("file_md5 不能为空")

            # 检查是否已存在
            existing_log = session.query(FileProcessingLog).filter(
                FileProcessingLog.file_md5 == file_md5
            ).first()

            if existing_log:
                # 更新现有记录
                for key, value in log_data.items():
                    if hasattr(existing_log, key):
                        setattr(existing_log, key, value)
                logger.info(f"更新处理日志: {file_md5}, 状态: {log_data.get('processing_status')}")
            else:
                # 插入新记录
                log = FileProcessingLog(**log_data)
                session.add(log)
                logger.info(f"创建处理日志: {file_md5}, 状态: {log_data.get('processing_status')}")

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"保存处理日志失败: {str(e)}")
            raise e
        finally:
            session.close()
