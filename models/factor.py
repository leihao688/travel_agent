from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from openai.types import ChatModel, EmbeddingModel
from typing import Optional, Union
from abc import ABC, abstractmethod
from config import Settings
from utils.config_load import rag_config

settings = Settings()


class BaseFactoryModel(ABC):
    @abstractmethod
    def generate(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class EmbeddingModelFactory(BaseFactoryModel):
    def generate(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(model=rag_config['embedding_model_name'])


class ChatModelFactory(BaseFactoryModel):
    def generate(self) -> Optional[Embeddings | BaseChatModel]:
        return ChatTongyi(model=rag_config['chat_model_name'])


chat_model = ChatModelFactory().generate()
embedding_model = EmbeddingModelFactory().generate()
