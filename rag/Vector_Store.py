import sys
import os

# 添加项目根目录到 sys.path，解决模块导入问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

import json
import os.path
import numpy as np
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from models.factor import embedding_model
from utils.config_load import chorma_config, rag_config
from utils.file_handle import listdir_with_allowed_type, get_file_md5_hex, file_loader
from utils.logger_tool import LogConfig
from utils.path_handle import get_absolute_path_with_base, get_project_root
from rag.MarkdownSmartSplitter import MarkdownSmartSplitter
from rag.RRFeRanker import RRFRanker
import re
import os
from sklearn.cluster import AgglomerativeClustering

log = LogConfig()
logger = log.get_logger(__name__)


class VectorStore:
    def __init__(self):
        self.embedding_model = embedding_model
        self.vector_store = Chroma(
            collection_name=chorma_config["collection_name"],
            embedding_function=self.embedding_model,
            persist_directory=get_absolute_path_with_base(get_project_root(), chorma_config["persist_directory"])
        )

        # 使用新的 MarkdownSmartSplitter
        self.markdown_splitter = MarkdownSmartSplitter(
            max_parent_length=chorma_config.get("max_parent_length", 500),
            chunk_size=chorma_config.get("chunk_size", 500),
            chunk_overlap=chorma_config.get("chunk_overlap", 50)
        )

        # 保留原有的 text_splitter 用于非 Markdown 文件
        self.text_splitter = None

        self.md5_file_path = get_absolute_path_with_base(
            get_project_root(), chorma_config["md5_hex_store"]
        )

        # 初始化 RRF 重排序器
        self.rrf_ranker = RRFRanker(k=60)

    def _is_noise_chunk(self, meta: dict) -> bool:
        """检查是否为噪声章节（仅检查 Header_2，避免 H1 误杀整个文档的 chunk）"""
        noise_headers = rag_config.get("noise_headers", ["附录"])
        header_val = meta.get('Header_2', '')
        if header_val and any(nh in header_val for nh in noise_headers):
            return True
        return False

    def get_retriever(self):
        """获取混合检索器（BM25 + 向量 + RRF 融合）"""
        docs = self.vector_store.get()
        if not docs['documents']:
            return self.vector_store.as_retriever()

        from langchain_core.documents import Document
        import jieba

        # BM25 使用 jieba 分词 + 小写化，解决中文无空格和英文大小写问题
        def chinese_tokenizer(text: str):
            return list(jieba.cut(text.lower()))

        documents = []
        for content, meta in zip(docs['documents'], docs['metadatas']):
            if self._is_noise_chunk(meta):
                continue
            documents.append(Document(page_content=content, metadata=meta))

        bm25_retriever = BM25Retriever.from_documents(
            documents,
            preprocess_func=chinese_tokenizer
        )
        bm25_retriever.k = rag_config["k"]

        # 向量检索：大幅多取，避免关键词查询时相关结果被遗漏
        overfetch_k = max(rag_config["k"] * 10, 30)
        vector_retriever = self.vector_store.as_retriever(
            search_kwargs={"k": overfetch_k}
        )

        rrf_k = rag_config.get("rrf_k", 60)
        self.rrf_ranker = RRFRanker(k=rrf_k)

        bm25_weight = rag_config.get("bm25_weight", 1.0)
        vector_weight = rag_config.get("vector_weight", 1.0)
        is_noise = self._is_noise_chunk

        class RRFRetriever:
            def __init__(self, bm25, vector, rrf_ranker, top_k):
                self.bm25 = bm25
                self.vector = vector
                self.rrf_ranker = rrf_ranker
                self.top_k = top_k

            def invoke(self, query: str):
                docs = self.rrf_ranker.rerank(
                    query=query,
                    retrievers=[self.bm25, self.vector],
                    top_k=self.top_k * 2,
                    weights=[bm25_weight, vector_weight]
                )
                filtered = [d for d in docs if not is_noise(d.metadata)]
                return filtered[:self.top_k]

        return RRFRetriever(bm25_retriever, vector_retriever, self.rrf_ranker, rag_config["k"])

    def load_file(self, dirfile: str):
        allow_path_file: tuple[str] = listdir_with_allowed_type(
            get_absolute_path_with_base(get_project_root(), dirfile),
            tuple(chorma_config["allow_knowledge_file_type"])
        )
        for file_path in allow_path_file:
            md5_hex = get_file_md5_hex(file_path)
            if not md5_hex:
                logger.error(f"获取文件MD5失败: {file_path}")
                continue
            if self.get_md5(md5_hex):
                logger.info(f"文件已存在: {file_path}")
                continue
            try:
                documents: list[Document] = file_loader(file_path)
                if not documents:
                    logger.error(f"文件解析失败: {file_path}")
                    continue

                all_splits = []
                for doc in documents:
                    if file_path.endswith(".txt"):
                        all_splits = self._process_txt(doc, file_path)
                    elif file_path.endswith(".pdf"):
                        all_splits = self._process_pdf(doc, file_path)
                    elif file_path.endswith(".md"):
                        all_splits = self._process_md(doc, file_path)

                if not all_splits:
                    logger.error(f"文件分块失败: {file_path}")
                    continue

                self.vector_store.add_documents(all_splits)
                self.save_md5(md5_hex)
                logger.info(f"文件已添加: {file_path}, 共{len(all_splits)}个分块")
            except Exception as e:
                logger.error(f"文件处理失败: {file_path},错误是：{str(e)}")

    def md5_exists(self, hex5_str: str) -> bool:
        if not os.path.exists(self.md5_file_path):
            open(self.md5_file_path, 'w', encoding='utf-8')
            return False
        with open(self.md5_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() == hex5_str:
                    return True
            return False

    def save_md5(self, md5_hex: str):
        with open(self.md5_file_path, 'a', encoding='utf-8') as f:
            f.write(md5_hex + "\n")

    def get_md5(self, md5_hex: str):
        if not os.path.exists(self.md5_file_path):
            return False
        with open(self.md5_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip() == md5_hex:
                    return True
            return False

    def _process_txt(self, doc: Document, file_path: str) -> list[Document]:
        all_splits = []
        """处理TXT文件（结构化解析，提取章节标题+正文，提升检索精度）"""
        sections = re.split(r'\n(?=[一二三四五六七八九十百]+、)', doc.page_content)
        is_structured = (
                len(sections) > 1 and
                re.match(r'[一二三四五六七八九十百]+、', sections[0])
        )

        if not is_structured:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chorma_config["chunk_size"],
                chunk_overlap=chorma_config["chunk_overlap"],
                separators=chorma_config["separators"],
                length_function=len
            )
            generic_docs = text_splitter.create_documents(
                [doc.page_content],
                metadatas=[{'source': os.path.basename(file_path)}]
            )
            all_splits.extend(generic_docs)
            return all_splits

        for section in sections:
            if not section.strip():
                continue

            title_match = re.match(r'([一二三四五六七八九十百]+、[^\n]+)', section)
            section_title = title_match.group(1) if title_match else "旅行攻略"

            body_start = section.find('\n')
            body_content = section[body_start + 1:].strip() if body_start != -1 else section.strip()

            if not body_content:
                continue

            from langchain_text_splitters import RecursiveCharacterTextSplitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chorma_config["chunk_size"],
                chunk_overlap=chorma_config["chunk_overlap"],
                separators=chorma_config["separators"],
                length_function=len
            )
            chapter_docs = text_splitter.create_documents(
                [body_content],
                metadatas=[{
                    'section_title': section_title,
                    'source': os.path.basename(file_path)
                }]
            )

            for chapter_doc in chapter_docs:
                chapter_doc.page_content = f"{section_title}\n{chapter_doc.page_content}"

            all_splits.extend(chapter_docs)
        return all_splits

    def get_topic(self, all_splits):
        if len(all_splits) > 1:
            logger.info(f"开始语义聚类，共{len(all_splits)}个分块...")
            embeds = []
            for i, d in enumerate(all_splits):
                embeds.append(self.embedding_model.embed_query(d.page_content))
                if (i + 1) % 5 == 0:
                    logger.info(f"已生成 {i + 1}/{len(all_splits)} 个向量...")

            embeds_array = np.array(embeds)

            clustering = AgglomerativeClustering(
                n_clusters=None, distance_threshold=0.6, linkage="average"
            )
            labels = clustering.fit_predict(embeds_array)

            for doc_obj, label in zip(all_splits, labels):
                doc_obj.metadata['theme_label'] = f"主题_{label}"

            logger.info(f"聚类完成，共{len(set(labels))}个主题")

    def _process_pdf(self, doc: Document, file_path: str) -> list[Document]:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chorma_config["chunk_size"],
            chunk_overlap=chorma_config["chunk_overlap"],
            separators=chorma_config["separators"],
            length_function=len
        )
        all_splits = []
        pdf_docs = text_splitter.create_documents(
            [doc.page_content],
            metadatas=[{'source': os.path.basename(file_path)}]
        )
        all_splits.extend(pdf_docs)
        self.get_topic(all_splits)
        return all_splits

    def _process_md(self, doc: Document, file_path: str) -> list[Document]:
        """处理Markdown文件 - 使用父子分块策略"""
        all_splits = []

        try:
            # 使用 MarkdownSmartSplitter 进行分割
            parent_chunks, child_chunks = self.markdown_splitter.split_text(
                doc.page_content,
                source=os.path.basename(file_path)
            )

            logger.info(f"Markdown 文件分割: {len(parent_chunks)} 个父块, {len(child_chunks)} 个子块")

            # 将父块存储到 MySQL
            from rag.ParentChunkStore import ParentChunkStore
            from utils.file_handle import get_file_md5_hex

            parent_store = ParentChunkStore()
            parent_data_list = []

            for parent in parent_chunks:
                # 统计该父块的子块数量
                parent_chunk_id = parent.metadata.get('parent_chunk_id', '')
                child_count = len([
                    c for c in child_chunks
                    if c.metadata.get('parent_chunk_id') == parent_chunk_id
                ])

                parent_data_list.append({
                    'chunk_id': parent_chunk_id,
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'file_md5': get_file_md5_hex(file_path),
                    'header_1': parent.metadata.get('Header_1', ''),
                    'header_2': parent.metadata.get('Header_2', ''),
                    'header_3': parent.metadata.get('Header_3', ''),
                    'full_content': parent.page_content,
                    'content_length': len(parent.page_content),
                    'child_count': child_count,
                    'metadata_json': json.dumps({
                        k: v for k, v in parent.metadata.items()
                        if k not in ['Header_1', 'Header_2', 'Header_3', 'parent_chunk_id']
                    }, ensure_ascii=False),
                    'chunk_index': int(parent.metadata.get('chunk_index', 0)),
                    'chroma_collection': chorma_config["collection_name"]
                })

            # 批量保存父块
            if parent_data_list:
                parent_store.batch_add_parent_chunks(parent_data_list)
                logger.info(f"父块已存储到 MySQL: {len(parent_data_list)} 条")

            # 只将子块添加到向量库
            all_splits.extend(child_chunks)

            return all_splits

        except Exception as e:
            logger.error(f"Markdown 处理失败: {str(e)}")
            raise e
