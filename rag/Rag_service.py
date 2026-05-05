from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
import asyncio
from rag.Vector_Store import VectorStore
from models.factor import chat_model
from utils.prompt_load import rag_prompts_load, rag_rewrite_prompts_load
from utils.logger_tool import get_logger

logger = get_logger(__name__)


class RagService:
    def __init__(self):
        self.vector_store = VectorStore()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_txt = rag_prompts_load()
        self.prompt_template = PromptTemplate.from_template(self.prompt_txt)
        self.model = chat_model
        self.chain = self.init_chain()
        self.query_rewrite_prompt = PromptTemplate.from_template(rag_rewrite_prompts_load())
        self.query_rewrite_chain = self.query_rewrite_prompt | self.model | StrOutputParser()

    def init_chain(self):
        chain = self.prompt_template | self.model | StrOutputParser()
        return chain

    def query_rewrite(self, query: str):
        try:
            result = self.query_rewrite_chain.invoke({
                "question": query
            })
            rewritten_query = result.strip()
            logger.info(f"查询重写: '{query}' → '{rewritten_query}'")
            return rewritten_query
        except Exception as e:
            logger.error(f"查询重写失败，使用原始查询: {str(e)}")
            return query

    def get_summary(self, query: str):
        try:
            rewrite_query = self.query_rewrite(query)
            docs = self.retriever.invoke(rewrite_query)
            if not docs:
                return "知识库中未找到相关信息"
            # 2. 格式化参考资料
            context_text = ""
            for i, doc in enumerate(docs):
                context_text += f"参考资料{i}: {doc.page_content}\n\n"

            # 3. 调用 LLM 链进行整合总结
            result = ""
            for chunk in self.chain.stream({"input": query, "context": context_text}):
                result += chunk

            return result.strip()
        except Exception as e:
            logger.error(f"RAG 总结失败：{str(e)}")
            return f"RAG 查询异常：{str(e)}"

    async def aget_summary(self, query: str) -> str:
        """异步方法：检索并整合 RAG 结果（供 MainAgent 工具调用）"""
        return await asyncio.to_thread(self.get_summary, query)


if __name__ == "__main__":
    rag = RagService()

    res = rag.get_summary("南京的城市编码")
    print(res)
