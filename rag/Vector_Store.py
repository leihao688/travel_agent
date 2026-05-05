import os.path
import numpy as np
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from models.factor import embedding_model
from utils.config_load import chorma_config, rag_config
from utils.file_handle import listdir_with_allowed_type, get_file_md5_hex, file_loader
from utils.logger_tool import LogConfig
from utils.path_handle import get_absolute_path_with_base, get_project_root
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
        # 混合分块的粗切，按标题进行分割
        headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
        ]
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chorma_config["chunk_size"],
            chunk_overlap=chorma_config["chunk_overlap"],
            separators=chorma_config["separators"],
            length_function=len
        )
        self.md5_file_path = get_absolute_path_with_base(
            get_project_root(), chorma_config["md5_hex_store"]
        )

    # 新增：BM25 检索器
    # 注意：需要先 add_documents 后才能初始化 BM25Retriever
    # 这里先留空，在 get_retriever 中动态创建

    def get_retriever(self):
        # weather_agent_prompt.txt. 获取 ChromaDB 中的所有文档
        docs = self.vector_store.get()
        if not docs['documents']:
            return self.vector_store.as_retriever()

        # 2. 将数据库内容转为 Document 对象列表
        from langchain_core.documents import Document

        documents = []
        for content, meta in zip(docs['documents'], docs['metadatas']):
            # 🔥 关键：从 metadata 提取所有层级标题并拼接到内容
            header_parts = []
            # 按层级顺序拼接：Header_1 > Header_2 > Header_3
            for level in ['Header_1', 'Header_2', 'Header_3']:
                if level in meta:
                    header_parts.append(meta[level])

            # 如果有标题，拼接到内容前面
            if header_parts:
                enhanced_content = " ".join(header_parts) + " " + content
            else:
                enhanced_content = content

            documents.append(Document(page_content=enhanced_content, metadata=meta))

        # 3. 创建 BM25 检索器
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = rag_config["k"]

        # 4. 创建向量检索器
        vector_retriever = self.vector_store.as_retriever(
            search_kwargs={"k": rag_config["k"]}
        )

        # 5. 融合：BM25 权重 0.4，向量权重 0.6
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.4, 0.6]
        )

        return ensemble_retriever

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
                    if file_path.endswith(".pdf"):
                        all_splits = self._process_pdf(doc, file_path)
                    if file_path.endswith(".md"):
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
        # 步骤1：尝试按中文序号分割
        sections = re.split(r'\n(?=[一二三四五六七八九十百]+、)', doc.page_content)
        # 🔥 兜底检测：如果只分出1块或第1块没有序号，说明不是结构化txt
        is_structured = (
                len(sections) > 1 and
                re.match(r'[一二三四五六七八九十百]+、', sections[0])
        )

        if not is_structured:
            generic_docs = self.text_splitter.create_documents(
                [doc.page_content],
                metadatas=[{'source': os.path.basename(file_path)}]
            )
            all_splits.extend(generic_docs)
        for section in sections:
            if not section.strip():
                continue

            # 2. 提取章节标题
            title_match = re.match(r'([一二三四五六七八九十百]+、[^\n]+)', section)
            section_title = title_match.group(1) if title_match else "旅行攻略"

            # 3. 提取正文
            body_start = section.find('\n')
            body_content = section[body_start + 1:].strip() if body_start != -1 else section.strip()

            # 4. 超过大小则按标点分块
            if not body_content:
                continue
                # 使用中文分块器处理正文
            chapter_docs = self.text_splitter.create_documents(
                [body_content],
                metadatas=[{
                    'section_title': section_title,
                    'source': os.path.basename(file_path)
                }]
            )

            # 将标题拼接到每个分块的内容前
            for chapter_doc in chapter_docs:
                chapter_doc.page_content = f"{section_title}\n{chapter_doc.page_content}"

            all_splits.extend(chapter_docs)
            # 步骤3：语义主题聚类
        # self.get_topic(all_splits)
        return all_splits

    def get_topic(self, all_splits):
        if len(all_splits) > 1:
            logger.info(f"开始语义聚类，共{len(all_splits)}个分块...")
            # weather_agent_prompt.txt. 将每个文本分块转化为高维向量
            embeds = []
            for i, d in enumerate(all_splits):
                embeds.append(self.embedding_model.embed_query(d.page_content))
                if (i + 1) % 5 == 0:
                    logger.info(f"已生成 {i + 1}/{len(all_splits)} 个向量...")

            # 2.将向量转化为Numpy数组以便后续的聚类算法使用
            embeds_array = np.array(embeds)

            # 3.根据向量相似度自动分组，相似内容归为一类
            clustering = AgglomerativeClustering(
                n_clusters=None, distance_threshold=0.6, linkage="average"
            )
            labels = clustering.fit_predict(embeds_array)

            # 4. 在 metadata 中增加主题标签
            for doc_obj, label in zip(all_splits, labels):
                doc_obj.metadata['theme_label'] = f"主题_{label}"

            logger.info(f"聚类完成，共{len(set(labels))}个主题")

    def _process_pdf(self, doc: Document, file_path: str) -> list[Document]:
        all_splits = []
        pdf_docs = self.text_splitter.create_documents(
            [doc.page_content],
            metadatas=[{'source': os.path.basename(file_path)}]
        )
        all_splits.extend(pdf_docs)
        self.get_topic(all_splits)
        return all_splits

    def _process_md(self, doc: Document, file_path: str) -> list[Document]:
        all_splits = []
        markdown_splits = self.markdown_splitter.split_text(doc.page_content)
        for split in markdown_splits:
            # 从 metadata 提取所有层级标题并拼接到内容
            header_parts = []
            for level in ['Header_1', 'Header_2', 'Header_3']:
                if level in split.metadata:
                    header_parts.append(split.metadata[level])

            if header_parts:
                enhanced_content = " ".join(header_parts) + "\n" + split.page_content
            else:
                enhanced_content = split.page_content
            md_docs = self.text_splitter.create_documents(
                [enhanced_content],
                metadatas=[{'source': os.path.basename(file_path)}]
            )
            all_splits.extend(md_docs)
        self.get_topic(all_splits)
        return all_splits


if __name__ == '__main__':
    data_path = get_absolute_path_with_base(get_project_root(), chorma_config["data_path"])

    print("正在加载数据...")
    vector_store = VectorStore()
    vector_store.load_file(data_path)
    retrieve = vector_store.get_retriever()
    res = retrieve.invoke("南京的城市编码是什么")
    print(res)
