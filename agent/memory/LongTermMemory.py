from models.factor import embedding_model, chat_model
from langchain_chroma import Chroma
import json
from utils.config_load import chorma_config
from utils.path_handle import get_absolute_path_with_base, get_project_root


class LongTermMemory:
    def __init__(self):
        self.embedding_model = embedding_model
        self.vector_store = Chroma(
            collection_name=chorma_config["memory_collection_name"],
            embedding_function=self.embedding_model,
            persist_directory=get_absolute_path_with_base(get_project_root(), chorma_config["persist_directory"])
        )
        self.chat_model = chat_model

    async def extract_summary(self, messages: list) -> str:
        """LLM 自动提取用户画像/偏好摘要"""
        prompt = f"""
        请从以下对话中提取用户的关键信息（身份、偏好、禁忌、习惯、预算偏好等）。
        只输出 JSON 格式，不要任何解释。格式如下：
        {{"preferences": ["偏好 1", "偏好 2"], "facts": ["事实 1", "事实 2"]}}

        对话内容：
        {json.dumps(messages[-10:], ensure_ascii=False, indent=2)}
        """
        try:
            res = await self.chat_model.ainvoke(prompt)
            content = res.content.strip()
            return content
        except Exception as e:
            print(f"LLM 提取用户信息摘要失败：{str(e)}")
            return json.dumps({"preferences": [], "facts": []}, ensure_ascii=False)

    async def store_summary(self, user_id: str, messages: list):
        """将用户画像/偏好摘要存储到向量库中"""
        if len(messages) < 4:  # 对话太短不存储
            return
        # 提取摘要
        summary = await self.extract_summary(messages)
        # 存入向量库
        self.vector_store.add_texts(texts=[summary], metadatas=[{"user_id": user_id}])
        print(f"✅ 长期记忆已保存：{user_id}")

    def retrieve(self, user_id: str, query: str) -> str:
        try:
            # 1.获取检索器
            retriever = self.vector_store.as_retriever(
                search_kwargs={"k": chorma_config["memory_k"],
                               "filter": {"user_id": user_id}}
            )
            # 2.执行检索（返回的是 Document 对象列表）
            docs = retriever.invoke(query)
            # 3. 提取文本内容并拼接
            if not docs:
                return "没有找到相关的历史记录"
            memories = [doc.page_content for doc in docs]
            return "\n".join(memories)

        except Exception as e:
            print(f"⚠️ 长期记忆检索失败：{e}")
            return ""
