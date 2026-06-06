from langchain_classic.chains.llm import LLMChain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
import asyncio
from utils.config_load import mysql_config
from rag.ParentChunkStore import ParentChunkStore
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
        # 初始化父块存储
        self.parent_store = ParentChunkStore()

    def build_chain(self):
        prompt = rag_prompts_load()

        llm = chat_model
        llm.temperature = 0.2

        template = PromptTemplate(
            input_variables=["context", "input"],
            template=prompt
        )
        return LLMChain(llm=llm, prompt=template)

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
            # 1. 改写查询以提升检索效果
            rewrite_query = self.query_rewrite(query)

            # 2. 检索相关子块
            docs = self.retriever.invoke(rewrite_query)
            if not docs:
                return "知识库中未找到相关信息"

            # 3. 兜底检查：验证检索结果是否包含查询关键词
            import jieba
            query_words = set(jieba.cut(query.lower()))
            stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要',
                         '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '吗', '吧', '呢', '？', '。', '！', '，', '、', '；',
                         '：', '（', '）', '【', '】', '《', '》', '"', "'", '“', '”', '‘', '’'}
            query_words = {w for w in query_words if w not in stopwords and len(w) > 1}

            has_match = False
            for doc in docs:
                # 检查文档内容
                doc_content = doc.page_content.lower()
                # 同时检查标题元数据（Header_3 通常包含景区级别信息）
                header_text = ''
                for level in ['Header_1', 'Header_2', 'Header_3']:
                    if level in doc.metadata and doc.metadata[level]:
                        header_text += str(doc.metadata[level]).lower()
                
                # 合并内容和标题进行检查
                full_text = doc_content + ' ' + header_text
                if any(word in full_text for word in query_words):
                    has_match = True
                    break

            if not has_match:
                logger.info(f"检索结果均不包含查询关键词 '{query}'，判定为不相关")
                return "知识库中未找到相关信息"

            # 4. 收集所有父块 ID
            parent_chunk_ids = []
            for doc in docs:
                parent_id = doc.metadata.get('parent_chunk_id')
                if parent_id and parent_id not in parent_chunk_ids:
                    parent_chunk_ids.append(parent_id)

            # 5. 批量从 MySQL 获取父块完整内容
            parent_chunks = {}
            if parent_chunk_ids:
                parents_data = self.parent_store.get_parents_by_ids(parent_chunk_ids)
                for parent in parents_data:
                    parent_chunks[parent['chunk_id']] = parent['full_content']

            # 6. 用父块内容替换子块，补充上下文
            enriched_docs = []
            for doc in docs:
                parent_id = doc.metadata.get('parent_chunk_id')
                if parent_id and parent_id in parent_chunks:
                    # 获取父块内容
                    parent_content = parent_chunks[parent_id]
                    
                    # 从标题中提取景区级别信息（如4A、5A）并添加到内容开头
                    header_3 = doc.metadata.get('Header_3', '')
                    import re
                    level_match = re.search(r'(\d+[A-Z])', str(header_3))
                    if level_match and '景区级别' not in parent_content:
                        # 在父块内容开头添加景区级别信息
                        parent_content = f"景区级别：{level_match.group(1)}\n{parent_content}"
                    
                    doc.page_content = parent_content
                    doc.metadata['content_source'] = 'parent_chunk'
                else:
                    doc.metadata['content_source'] = 'child_chunk'
                enriched_docs.append(doc)

            # 7. 格式化检索结果为上下文文本
            context_text = ""
            for i, doc in enumerate(enriched_docs):
                rrf_score = doc.metadata.get('rrf_score', 0)
                source = doc.metadata.get('source', '未知')
                content_source = doc.metadata.get('content_source', 'unknown')

                header_info = []
                for level in ['Header_1', 'Header_2', 'Header_3']:
                    if level in doc.metadata and doc.metadata[level]:
                        header_info.append(doc.metadata[level])
                
                # 将标题信息合并到内容中，确保LLM能看到完整信息
                content_with_title = doc.page_content
                if header_info:
                    content_with_title = f"【标题】{' > '.join(header_info)}\n{content_with_title}"

                context_text += f"参考资料{i} (RRF={rrf_score:.4f}, 来源={source}, 内容类型={content_source}):\n"
                context_text += f"内容: {content_with_title}\n\n"

            # 8. 调用 LLM 基于上下文生成回答
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

    res = rag.get_summary("北京的天气编码")
    print(res)
