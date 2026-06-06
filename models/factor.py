from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from typing import Optional
from abc import ABC, abstractmethod
from utils.config_load import rag_config


class BaseFactoryModel(ABC):
    @abstractmethod
    def generate(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class EmbeddingModelFactory(BaseFactoryModel):
    def generate(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(model=rag_config['embedding_model_name'])


class ChatModelFactory(BaseFactoryModel):
    def generate(self) -> Optional[Embeddings | BaseChatModel]:
        # 🔥 使用 OpenAI 兼容接口调用 DashScope，支持 qwen3.6-plus 多模态模型
        return ChatOpenAI(
            model=rag_config['chat_model_name'],
            openai_api_key=rag_config.get('dashscope_api_key', ''),
            openai_api_base='https://dashscope.aliyuncs.com/compatible-mode/v1',
            streaming=True,
        )


# 🔥 修改：提供工厂函数，每次调用返回新实例
def create_chat_model() -> BaseChatModel:
    """创建新的聊天模型实例（避免并发冲突）"""
    return ChatModelFactory().generate()


def create_embedding_model() -> Embeddings:
    """创建新的嵌入模型实例"""
    return EmbeddingModelFactory().generate()


chat_model = ChatModelFactory().generate()
embedding_model = EmbeddingModelFactory().generate()
