"""
Markdown智能分块器 - 支持父子块架构
借鉴 Chunkdown 理念，专为 Python + LangChain 项目设计

核心特性：
1. 基于标题层级的语义分割（一级分割）
2. 对过大父块的二次分割（二级分割）
3. 特殊结构保护（表格、代码块、引用块）
4. 可控溢出机制（max_overflow_ratio）
5. 内容长度计算（可选，排除Markdown格式字符）
6. 面包屑上下文（ancestor headings）
"""
import sys
import os

# 添加项目根目录到 sys.path，解决模块导入问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

import re
from collections import Counter
from typing import Dict, List

import jieba
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

from utils.logger_tool import get_logger

logger = get_logger(__name__)


def calculate_token_count(text: str) -> int:
    """
    计算文本的 token 数量（使用通义千问 tokenizer）

    Args:
        text: 输入文本

    Returns:
        token 数量
    """
    if not text:
        return 0

    try:
        from dashscope import get_tokenizer
        from utils.config_load import rag_config

        # 获取模型名称
        model_name = rag_config.get('chat_model_name', 'qwen-turbo')

        # 使用通义千问的 tokenizer，需要传入 model 参数
        tokenizer = get_tokenizer(model_name)
        tokens = tokenizer.encode(text)
        return len(tokens)
    except Exception as e:
        logger.warning(f"Token 计算失败，回退到字符计数: {e}")
        # 备用方案：中英文混合估算
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))
        english_words = len(re.findall(r'\b[a-zA-Z][a-zA-Z-]*\b', text))
        return int(chinese_chars * 1.5 + english_words * 1.3 + (len(text) - chinese_chars) * 0.5)


class MarkdownSmartSplitter:
    """
    Markdown智能分块器 - 父子块架构

    工作流程：
    1. 分析文档结构（标题层级、特殊结构）
    2. 决定父块分割层级（H2优先 → H3次之 → 整体）
    3. 执行一级分割（按标题生成父块）
    4. 保护特殊结构（表格/代码块不拆分）
    5. 对过大父块执行二级分割（RecursiveCharacterTextSplitter）
    6. 生成子块并关联父块ID
    7. 返回父块列表（存MySQL）和子块列表（存ChromaDB）
    """

    def __init__(
            self,
            chunk_size: int = 500,
            chunk_overlap: int = 50,
            max_parent_length: int = 2000,
            max_overflow_ratio: float = 1.5,
            use_content_length: bool = False,
            use_token_count: bool = True
    ):
        """
            初始化分块器

            Args:
                chunk_size: 子块目标大小（字符数）
                chunk_overlap: 子块重叠（字符数）
                max_parent_length: 父块最大长度（超过则二次分割）
                max_overflow_ratio: 最大溢出比例（1.0=不允许溢出，1.5=允许50%溢出）
                use_content_length: 是否使用内容长度计算（排除Markdown格式字符）
        """
        self.use_token_count = use_token_count
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_parent_length = max_parent_length
        self.max_overflow_ratio = max_overflow_ratio
        self.use_content_length = use_content_length

        # 分隔符优先级：句号 > 分号 > 感叹号 > 问号 > 空格 > 换行
        self.separators = ["。", "；", "！", "？", " ", "\n\n", "\n"]
        # 使用 LangChain 的 Markdown 标题分割器（一级分割）
        headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
        ]
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        # 初始化递归字符分块器（用于二级分割）
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len
        )

    def _get_length(self, text: str) -> int:
        """
        获取文本长度（支持 token 计数和字符计数）

        Args:
            text: 输入文本

        Returns:
            长度（token数或字符数）
        """
        if self.use_token_count:
            return calculate_token_count(text)
        return len(text)

    def calculate_content_length(self, markdown_text: str) -> int:
        """
        计算纯文本内容长度，排除 Markdown 格式字符

        Args:
            markdown_text: Markdown 文本

        Returns:
            纯文本字符数或token数
        """
        if not self.use_content_length:
            return self._get_length(markdown_text)

        text = markdown_text

        # 移除链接格式：[text](url) → text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # 移除图片格式：![alt](url) → alt
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)

        # 移除粗体/斜体标记：**text** → text, *text* → text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # 移除删除线：~~text~~ → text
        text = re.sub(r'~~([^~]+)~~', r'\1', text)

        # 移除行内代码：`code` → code
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 移除标题标记：# Heading → Heading
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

        # 移除列表标记：- item → item, 1. item → item
        text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)

        # 移除引用标记：> text → text
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

        # 移除水平线：---, ***, ___
        text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

        return self._get_length(text)

    @staticmethod
    def extract_keywords(text: str, top_k: int = 8) -> List[str]:
        """
        从文本中提取关键词

        使用 jieba 分词 + TF-IDF 思想提取关键词

        Args:
            text: 文本内容
            top_k: 提取的关键词数量

        Returns:
            关键词列表
        """
        try:
            # 使用 jieba 分词
            words = jieba.lcut(text)

            # 过滤停用词和短词
            stopwords = {
                '的', '了', '在', '是', '我', '有', '和', '就',
                '不', '人', '都', '一', '一个', '上', '也', '很',
                '到', '说', '要', '去', '你', '会', '着', '没有',
                '看', '好', '自己', '这', '那', '吗', '吧', '呢'
            }

            filtered_words = [
                word for word in words
                if word not in stopwords
                   and len(word.strip()) > 1
                   and not word.isspace()
                   and not word.startswith('#')  # 过滤 Markdown 标题标记
                   and not word.startswith('```')
                   and not word.startswith('>') # 过滤引用块标记

            ]

            # 统计词频
            word_counts = Counter(filtered_words)

            # 返回 top_k 个关键词
            keywords = [word for word, count in word_counts.most_common(top_k)]

            return keywords

        except Exception as e:
            logger.warning(f"关键词提取失败: {str(e)}")
            return []

    @staticmethod
    def contains_special_structure(content: str) -> bool:
        """ 检查内容是否包含不可分割的特殊结构

        不可分割的10种元素：
        1. 代码块(```)
        2. 表格（|列|列|）
        3. 引用块（>）
        4. 链接（text）
        5. 图片（ ）
        6. 行内代码（code）
        7. 数学公式（$...$ 或 $$...$$）
        8. HTML 块标签（<div>, <table> 等）
        9. 脚注（[^note]）
        10. 连续列表（- item 或 1. item）
        """
        # 1. 代码块
        has_code_block = '```' in content

        # 2. 表格
        has_table = re.search(r'^\s*\|.*\|', content, re.MULTILINE) is not None

        # 3. 引用块
        has_quote = re.search(r'^\s*>', content, re.MULTILINE) is not None

        # 4. 链接（内联式和参考式）
        has_link = (
                re.search(r'\[([^\]]+)\]\([^)]+\)', content) is not None or
                re.search(r'\[([^\]]+)\]\[([^\]]+)\]', content) is not None
        )

        # 5. 图片（内联式和参考式）
        has_image = (
                re.search(r'!\[([^\]]*)\]\([^)]+\)', content) is not None or
                re.search(r'!\[([^\]]*)\]\[([^\]]+)\]', content) is not None
        )

        # 6. 行内代码
        has_inline_code = re.search(r'`[^`]+`', content) is not None

        # 7. 数学公式（单行 $...$ 和多行 $$...$$）
        has_math = (
                re.search(r'\$\$.+?\$\$', content, re.DOTALL) is not None or
                re.search(r'(?<!\$)\$(?!\$).+?(?<!\$)\$(?!\$)', content) is not None
        )

        # 8. HTML 块标签
        has_html_block = re.search(
            r'<(div|table|ul|ol|li|p|header|footer|section|article'
            r'|aside|nav|main|form|blockquote|pre|hr|figure|figcaption|details|summary)[^>]*>',
            content,
            re.IGNORECASE
        ) is not None

        # 9. 脚注
        has_footnote = re.search(r'\[\^[^\]]+\]', content) is not None

        # 10. 连续列表（有序或无序，至少2项）
        # 这里是重点：去掉了列表正则里的冗余转义（实际上你这里是对的，IDE误报？）
        has_unordered_list = (
                re.search(r'^[-*+]\s+.+?$', content, re.MULTILINE) is not None and
                len(re.findall(r'^[-*+]\s+', content, re.MULTILINE)) >= 2
        )
        has_ordered_list = (
                re.search(r'^\d+\.\s+.+?$', content, re.MULTILINE) is not None and
                len(re.findall(r'^\d+\.\s+', content, re.MULTILINE)) >= 2
        )
        has_list = has_unordered_list or has_ordered_list

        return (has_code_block or has_table or has_quote or has_link or
                has_image or has_inline_code or has_math or has_html_block or
                has_footnote or has_list)

    def secondary_split(self, chunk_content: str, metadata: Dict, parent_id: str) -> List[Document]:
        """
        对过大的父块进行二级分割

        策略：
        1. 提取所有特殊结构
        2. 大型特殊结构（> 750字符）→ 智能分割后输出
        3. 普通文本区域 → 正常分割
        4. 小型特殊结构 → 和普通文本一起分割（但本身保持完整）
        5. 支持 chunk_overlap 重叠机制
        """

        # 提取所有段
        segments = self._extract_segments(chunk_content)
        large_special_threshold = self.chunk_size * 1.5

        child_docs = []
        sub_idx = 0

        # 累积需要分割的内容（普通文本 + 小型特殊结构）
        current_text_parts = []
        current_length = 0

        # 重叠机制：保存上一块的末尾内容
        last_block_tail = ""

        for segment in segments:
            segment_length = self._get_length(segment['content'])

            if segment['is_special'] and segment_length > large_special_threshold:
                # 大型特殊结构：先分割已累积的文本
                if current_text_parts:
                    combined_text = '\n'.join(current_text_parts)
                    # 添加重叠内容
                    if last_block_tail:
                        combined_text = last_block_tail + '\n' + combined_text

                    docs = self._safe_split(combined_text, metadata, parent_id)
                    for doc in docs:
                        doc.metadata['sub_chunk_index'] = sub_idx
                        sub_idx += 1
                    child_docs.extend(docs)

                    # 保存当前块的末尾作为下一块的重叠
                    if docs:
                        last_block_tail = docs[-1].page_content[-self.chunk_overlap:]

                    current_text_parts = []
                    current_length = 0

                # 大型特殊结构：根据类型调用相应的分割方法
                if segment['type'] == 'table':
                    table_chunks = self._split_table_with_header(segment['content'])
                    for chunk in table_chunks:
                        # 表格分割自带表头，不需要额外重叠
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'table'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                    # 保存最后一个表格块的末尾
                    if table_chunks:
                        last_block_tail = table_chunks[-1][-self.chunk_overlap:]
                elif segment['type'] == 'code_block':
                    code_chunks = self._split_code_block(segment['content'])
                    for chunk in code_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'code_block'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                    if code_chunks:
                        last_block_tail = code_chunks[-1][-self.chunk_overlap:]
                elif segment['type'] == 'quote':
                    quote_chunks = self._split_quote_block(segment['content'])
                    for chunk in quote_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'quote'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                    if quote_chunks:
                        last_block_tail = quote_chunks[-1][-self.chunk_overlap:]
                elif segment['type'] == 'math_block':
                    math_chunks = self._split_math_block(segment['content'])
                    for chunk in math_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'math_block'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                    if math_chunks:
                        last_block_tail = math_chunks[-1][-self.chunk_overlap:]
                elif segment['type'] == 'html_block':
                    html_chunks = self._split_html_block(segment['content'])
                    for chunk in html_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'html_block'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                    if html_chunks:
                        last_block_tail = html_chunks[-1][-self.chunk_overlap:]
                else:
                    # 其他类型直接作为整体
                    special_doc = Document(
                        page_content=segment['content'],
                        metadata={
                            **metadata,
                            'parent_chunk_id': parent_id,
                            'sub_chunk_index': sub_idx,
                            'has_special_structure': True,
                            'special_type': segment['type']
                        }
                    )
                    child_docs.append(special_doc)
                    sub_idx += 1
                    last_block_tail = segment['content'][-self.chunk_overlap:]
            else:
                # 普通文本 或 小型特殊结构：累积起来一起分割
                current_text_parts.append(segment['content'])
                current_length += segment_length

                # 累积到阈值，先分割
                if current_length > self.chunk_size:
                    combined_text = '\n'.join(current_text_parts)
                    # 添加重叠内容
                    if last_block_tail:
                        combined_text = last_block_tail + '\n' + combined_text

                    docs = self._safe_split(combined_text, metadata, parent_id)
                    for doc in docs:
                        doc.metadata['sub_chunk_index'] = sub_idx
                        sub_idx += 1
                    child_docs.extend(docs)

                    # 保存当前块的末尾作为下一块的重叠
                    if docs:
                        last_block_tail = docs[-1].page_content[-self.chunk_overlap:]

                    current_text_parts = []
                    current_length = 0

        # 处理剩余的文本
        if current_text_parts:
            combined_text = '\n'.join(current_text_parts)
            # 添加重叠内容
            if last_block_tail:
                combined_text = last_block_tail + '\n' + combined_text

            docs = self._safe_split(combined_text, metadata, parent_id)
            for doc in docs:
                doc.metadata['sub_chunk_index'] = sub_idx
                sub_idx += 1
            child_docs.extend(docs)

        return child_docs

    def _split_table_with_header(self, table_content: str) -> List[str]:
        """分割表格时在每个 chunk 中保留表头"""
        lines = table_content.strip().split('\n')
        if len(lines) < 3:
            return [table_content]

        header_line = lines[0]  # 表头
        separator_line = lines[1]  # 分隔线
        data_lines = lines[2:]  # 数据行

        chunks = []
        current_lines = [header_line, separator_line]
        current_length = self._get_length(header_line) + self._get_length(separator_line)

        for data_line in data_lines:
            # 检测单行是否过长
            if self._get_length(data_line) > self.chunk_size * 2:
                logger.warning(
                    f"表格单行过长({self._get_length(data_line)}字符)，可能影响检索效果，"
                    f"建议简化表格内容"
                )

            if current_length + self._get_length(data_line) > self.chunk_size and len(current_lines) > 2:
                # 超过子块大小，输出当前 chunk
                chunks.append('\n'.join(current_lines))
                # 新 chunk 从表头开始
                current_lines = [header_line, separator_line, data_line]
                current_length = self._get_length(header_line) + self._get_length(separator_line) + self._get_length(
                    data_line)
            else:
                current_lines.append(data_line)
                current_length += self._get_length(data_line)

        # 输出最后一个 chunk
        if len(current_lines) > 2:
            chunks.append('\n'.join(current_lines))

        # 合并过小的末尾块
        chunks = self._merge_small_chunks(chunks)

        return chunks if chunks else [table_content]

    def _split_code_block(self, code_content: str) -> List[str]:
        """分割代码块时保留语言标识"""
        lines = code_content.strip().split('\n')
        if len(lines) < 3:
            return [code_content]

        # 提取语言标识（第一行）
        lang_line = lines[0]
        chunks = []
        current_lines = [lang_line]
        current_length = self._get_length(lang_line)
        code_lines = lines[1:-1]  # 中间的代码
        end_line = lines[-1]  # 最后一行：
        for code_line in code_lines:
            if current_length + self._get_length(code_line) > self.chunk_size and len(current_lines) > 1:
                # 超过子块大小，输出当前 chunk
                current_lines.append(end_line)  # 添加结束标记
                chunks.append('\n'.join(current_lines))
                # 新 chunk 从语言标识开始
                current_lines = [lang_line, code_line]
                current_length = self._get_length(lang_line) + self._get_length(code_line)
            else:
                current_lines.append(code_line)
                current_length += self._get_length(code_line)

        # 输出最后一个 chunk
        if len(current_lines) > 1:
            current_lines.append(end_line)
            chunks.append('\n'.join(current_lines))

        # 合并过小的末尾块
        chunks = self._merge_small_chunks(chunks)

        return chunks if chunks else [code_content]

    def _split_quote_block(self, quote_content: str) -> List[str]:
        """分割引用块时保留引用标记"""
        lines = quote_content.strip().split('\n')
        if len(lines) < 3:
            return [quote_content]

        chunks = []
        current_lines = []
        current_length = 0

        for line in lines:
            if current_length + self._get_length(line) > self.chunk_size and current_lines:
                # 超过子块大小，输出当前 chunk
                chunks.append('\n'.join(current_lines))
                # 新 chunk 从当前行开始
                current_lines = [line]
                current_length = self._get_length(line)
            else:
                current_lines.append(line)
                current_length += self._get_length(line)

        # 输出最后一个 chunk
        if current_lines:
            chunks.append('\n'.join(current_lines))

        # 合并过小的末尾块
        chunks = self._merge_small_chunks(chunks)

        return chunks if chunks else [quote_content]

    def _split_math_block(self, math_content: str) -> List[str]:
        """分割数学公式块时保留 $$ 标记"""
        lines = math_content.strip().split('\n')
        if len(lines) < 3:
            return [math_content]

        chunks = []
        current_lines = [lines[0]]  # 保留开头的 $$
        current_length = self._get_length(lines[0])
        formula_lines = lines[1:-1]  # 中间的公式内容
        end_line = lines[-1]  # 结尾的 $$

        for formula_line in formula_lines:
            if current_length + self._get_length(formula_line) > self.chunk_size and len(current_lines) > 1:
                # 超过子块大小，输出当前 chunk
                current_lines.append(end_line)
                chunks.append('\n'.join(current_lines))
                # 新 chunk 从开头标记开始
                current_lines = [lines[0], formula_line]
                current_length = self._get_length(lines[0]) + self._get_length(formula_line)
            else:
                current_lines.append(formula_line)
                current_length += self._get_length(formula_line)

        # 输出最后一个 chunk
        if len(current_lines) > 1:
            current_lines.append(end_line)
            chunks.append('\n'.join(current_lines))

        # 合并过小的末尾块
        chunks = self._merge_small_chunks(chunks)

        return chunks if chunks else [math_content]

    def _split_html_block(self, html_content: str) -> List[str]:
        """分割HTML块时尽量保持标签完整性"""
        # HTML块不建议分割，直接返回
        return [html_content]

    @staticmethod
    def _extract_segments(content: str) -> List[Dict]:
        """
        提取内容中的所有段（普通文本和特殊结构）

        Args:
            content: Markdown 内容

        Returns:
            段列表，每个段包含：
            - content: 段内容
            - is_special: 是否为特殊结构
            - type: 特殊结构类型（code_block, table, quote, normal）
        """
        segments = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # 1. 检测代码块
            if line.strip().startswith('```'):
                code_lines = [line]
                i += 1
                while i < len(lines):
                    code_lines.append(lines[i])
                    if lines[i].strip().startswith('```') and len(code_lines) > 1:
                        i += 1
                        break
                    i += 1
                segments.append({
                    'content': '\n'.join(code_lines),
                    'is_special': True,
                    'type': 'code_block'
                })
                continue

            # 2. 检测表格（至少两行且包含 | ）
            if '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
                table_lines = [line]
                i += 1
                # 添加分隔行
                table_lines.append(lines[i])
                i += 1
                # 继续收集表格数据行
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                segments.append({
                    'content': '\n'.join(table_lines),
                    'is_special': True,
                    'type': 'table'
                })
                continue

            # 3. 检测引用块
            if line.strip().startswith('>'):
                quote_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip().startswith('>'):
                    quote_lines.append(lines[i])
                    i += 1
                segments.append({
                    'content': '\n'.join(quote_lines),
                    'is_special': True,
                    'type': 'quote'
                })
                continue
                # 4. 检测数学公式块（$$...$$）
            if line.strip().startswith('$$'):
                math_lines = [line]
                i += 1
                while i < len(lines):
                    math_lines.append(lines[i])
                    if lines[i].strip().endswith('$$') and len(math_lines) > 1:
                        i += 1
                        break
                    i += 1
                segments.append({
                    'content': '\n'.join(math_lines),
                    'is_special': True,
                    'type': 'math_block'
                })
                continue
                # 5. 检测HTML块标签
            html_match = re.match(
                r'^\s*<(div|table|ul|ol|p|blockquote|pre|figure|details)[^>]*>',
                line,
                re.IGNORECASE
            )
            if html_match:
                tag_name = html_match.group(1).lower()
                html_lines = [line]
                i += 1
                # 尝试找到闭合标签
                close_pattern = re.compile(rf'</{tag_name}>', re.IGNORECASE)
                found_close = False
                while i < len(lines):
                    html_lines.append(lines[i])
                    if close_pattern.search(lines[i]):
                        found_close = True
                        i += 1
                        break
                    i += 1
                # 即使没找到闭合标签，也作为特殊结构保存
                segments.append({
                    'content': '\n'.join(html_lines),
                    'is_special': True,
                    'type': 'html_block'
                })
                continue

            # 6.普通文本行
            segments.append({
                'content': line,
                'is_special': False,
                'type': 'normal'
            })
            i += 1

        return segments

    def _safe_split(self, text: str, metadata: Dict, parent_id: str) -> List[Document]:
        """
        安全分割文本，保护特殊结构不被破坏

        策略：
        1. 小型特殊结构（<= chunk_size）与普通文本组合
        2. 大型特殊结构（> chunk_size）需要智能拆分：
           - 表格：保留表头，按行拆分
           - 代码块：保留语言标识，按行拆分
           - 引用块：保留引用标记，按行拆分
        3. 纯普通文本按 chunk_size 智能分割
        4. 混合内容（特殊结构+普通文本）手动控制分割点

        Args:
            text: 待分割的文本
            metadata: 元数据
            parent_id: 父块 ID

        Returns:
            子块文档列表
        """
        # 检查是否包含特殊结构
        if not self.contains_special_structure(text):
            # 没有特殊结构，直接分割
            docs = self.text_splitter.create_documents([text], metadatas=[metadata])
            for doc in docs:
                doc.metadata['parent_chunk_id'] = parent_id
            return docs

        # 包含特殊结构，需要特殊处理
        segments = self._extract_segments(text)
        child_docs = []
        sub_idx = 0

        current_text_parts = []
        current_length = 0
        special_types_in_current = set()

        for segment in segments:
            segment_length = self._get_length(segment['content'])

            # 如果当前段是大型特殊结构，先处理已累积的内容
            if segment['is_special'] and segment_length > self.chunk_size:
                # 先分割已累积的内容
                if current_text_parts:
                    combined_text = '\n'.join(current_text_parts)
                    if special_types_in_current:
                        # 包含特殊结构，不能智能分割，直接作为一个子块
                        doc = Document(
                            page_content=combined_text,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': ', '.join(sorted(special_types_in_current))
                            }
                        )
                        child_docs.append(doc)
                    else:
                        # 纯普通文本，用智能分割
                        docs = self.text_splitter.create_documents(
                            [combined_text],
                            metadatas=[metadata]
                        )
                        for d in docs:
                            d.metadata['parent_chunk_id'] = parent_id
                            d.metadata['sub_chunk_index'] = sub_idx
                            sub_idx += 1
                        child_docs.extend(docs)
                    current_text_parts = []
                    current_length = 0
                    special_types_in_current = set()

                # 处理大型特殊结构
                if segment['type'] == 'table':
                    table_chunks = self._split_table_with_header(segment['content'])
                    for chunk in table_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'table'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                elif segment['type'] == 'code_block':
                    code_chunks = self._split_code_block(segment['content'])
                    for chunk in code_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'code_block'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                elif segment['type'] == 'quote':
                    quote_chunks = self._split_quote_block(segment['content'])
                    for chunk in quote_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'quote'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                elif segment['type'] == 'math_block':
                    math_chunks = self._split_math_block(segment['content'])
                    for chunk in math_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'math_block'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                elif segment['type'] == 'html_block':
                    html_chunks = self._split_html_block(segment['content'])
                    for chunk in html_chunks:
                        special_doc = Document(
                            page_content=chunk,
                            metadata={
                                **metadata,
                                'parent_chunk_id': parent_id,
                                'sub_chunk_index': sub_idx,
                                'has_special_structure': True,
                                'special_type': 'html_block'
                            }
                        )
                        child_docs.append(special_doc)
                        sub_idx += 1
                continue

            # 检查加入当前段后是否会超过 chunk_size
            if current_length + segment_length > self.chunk_size and current_length > 0:
                # 先分割已累积的内容
                combined_text = '\n'.join(current_text_parts)
                if special_types_in_current:
                    # 包含特殊结构，直接作为一个子块
                    doc = Document(
                        page_content=combined_text,
                        metadata={
                            **metadata,
                            'parent_chunk_id': parent_id,
                            'sub_chunk_index': sub_idx,
                            'has_special_structure': True,
                            'special_type': ', '.join(sorted(special_types_in_current))
                        }
                    )
                    child_docs.append(doc)
                else:
                    # 纯普通文本，用智能分割
                    docs = self.text_splitter.create_documents(
                        [combined_text],
                        metadatas=[metadata]
                    )
                    for d in docs:
                        d.metadata['parent_chunk_id'] = parent_id
                        d.metadata['sub_chunk_index'] = sub_idx
                        sub_idx += 1
                    child_docs.extend(docs)
                current_text_parts = []
                current_length = 0
                special_types_in_current = set()

            # 累积当前段
            current_text_parts.append(segment['content'])
            current_length += segment_length
            if segment['is_special']:
                special_types_in_current.add(segment['type'])

        # 处理剩余内容
        if current_text_parts:
            combined_text = '\n'.join(current_text_parts)
            if special_types_in_current:
                doc = Document(
                    page_content=combined_text,
                    metadata={
                        **metadata,
                        'parent_chunk_id': parent_id,
                        'sub_chunk_index': sub_idx,
                        'has_special_structure': True,
                        'special_type': ', '.join(sorted(special_types_in_current))
                    }
                )
                child_docs.append(doc)
            else:
                docs = self.text_splitter.create_documents(
                    [combined_text],
                    metadatas=[metadata]
                )
                for d in docs:
                    d.metadata['parent_chunk_id'] = parent_id
                    d.metadata['sub_chunk_index'] = sub_idx
                    sub_idx += 1
                child_docs.extend(docs)

        # 过滤过短的子块（< 30字符且主要是标题标记的孤立块）
        min_chunk_size = 30
        child_docs = [
            d for d in child_docs
            if self._get_length(d.page_content) >= min_chunk_size
        ]
        # 为每个子块提取关键词
        for doc in child_docs:
            keywords = self.extract_keywords(doc.page_content)
            if keywords:
                doc.metadata['keywords'] = keywords

        return child_docs

    def _decide_split_level(self, markdown_text: str) -> int:
        """
        决定父块分割层级

        策略：
        1. 统计 H2、H3 标题数量
        2. H2 ≥ 3 个 → 按 H2 分割（level=2）
        3. H3 ≥ 3 个 → 按 H3 分割（level=3）
        4. 否则整体作为一个父块（level=0）

        Args:
            markdown_text: Markdown 文本

        Returns:
            分割层级（0=整体，2=H2，3=H3）
        """
        h2_count = len(re.findall(r'^##\s+', markdown_text, re.MULTILINE))
        h3_count = len(re.findall(r'^###\s+', markdown_text, re.MULTILINE))

        if h2_count >= 3:
            return 2
        elif h3_count >= 3:
            return 3
        else:
            return 0

    def split_text(self, markdown_text: str, source: str = "") -> tuple[List[Document], List[Document]]:
        """
        主要分块入口方法 - 父子块架构

        工作流程：
        1. 分析文档结构，决定分割层级
        2. 执行一级分割（按标题生成父块）
        3. 对过大父块执行二级分割
        4. 返回父块列表和子块列表

        Args:
            markdown_text: Markdown 文本
            source: 来源文件名

        Returns:
            (父块列表, 子块列表)
            - 父块：存 MySQL，包含纯净内容和标题路径
            - 子块：存 ChromaDB，包含增强内容（标题+正文）
        """
        import uuid

        # 步骤1：决定分割层级
        split_level = self._decide_split_level(markdown_text)

        parent_chunks = []
        child_chunks = []

        if split_level == 0:
            # 整体作为一个父块
            parent_id = str(uuid.uuid4())
            needs_secondary = self._get_length(markdown_text) > self.max_parent_length

            parent_metadata = {
                'source': source,
                'chunk_level': 0,
                'has_sub_chunks': needs_secondary
            }

            # 创建父块
            parent_doc = Document(
                page_content=markdown_text,
                metadata={
                    **parent_metadata,
                    'parent_chunk_id': parent_id,
                    'chunk_type': 'parent'
                }
            )
            parent_chunks.append(parent_doc)

            if needs_secondary:
                child_docs = self.secondary_split(markdown_text, parent_metadata, parent_id)
                child_chunks.extend(child_docs)
            else:
                # 不需要二级分割，父块本身也作为子块
                child_doc = Document(
                    page_content=markdown_text,
                    metadata={
                        **parent_metadata,
                        'parent_chunk_id': parent_id,
                        'sub_chunk_index': 0,
                        'chunk_type': 'child'
                    }
                )
                # 提取关键词
                keywords = self.extract_keywords(markdown_text)
                if keywords:
                    child_doc.metadata['keywords'] = keywords
                child_chunks.append(child_doc)
        else:
            # 按标题层级分割
            headers_to_split_on = []
            if split_level >= 2:
                headers_to_split_on.append(("##", "Header_2"))
            if split_level >= 3:
                headers_to_split_on.append(("###", "Header_3"))

            # 使用 MarkdownHeaderTextSplitter 进行一级分割
            temp_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on
            )
            sections = temp_splitter.split_text(markdown_text)

            for section in sections:
                if not section.page_content.strip():
                    continue

                # 过滤纯标题块（无实质正文内容）
                body_text = re.sub(r'^#+\s+.*$', '', section.page_content, flags=re.MULTILINE).strip()
                
                # 降低阈值：允许短内容的键值对类型数据（如城市ID编码）
                # 对于结构化数据（如"城市ID：xxx"），即使内容短也应该保留
                if self._get_length(body_text) < 20:
                    # 检查是否为键值对格式（如"城市ID：xxx"），如果是则保留
                    if not re.search(r'[：:]', body_text):
                        continue

                parent_id = str(uuid.uuid4())

                # 构建标题路径
                header_path = []
                for level in ['Header_1', 'Header_2', 'Header_3']:
                    if level in section.metadata:
                        header_path.append(section.metadata[level])

                # 先判断是否需要二级分割
                content_length = self.calculate_content_length(section.page_content)
                needs_secondary = content_length > self.max_parent_length

                # 父块元数据
                parent_metadata = {
                    'source': source,
                    'chunk_level': split_level,
                    'has_sub_chunks': needs_secondary,
                    **{k: v for k, v in section.metadata.items() if k.startswith('Header_')}
                }

                # 创建父块（纯净内容）
                parent_doc = Document(
                    page_content=section.page_content,
                    metadata={
                        **parent_metadata,
                        'parent_chunk_id': parent_id,
                        'chunk_type': 'parent'
                    }
                )
                parent_chunks.append(parent_doc)

                # 子块存储纯净内容（不拼接标题），标题路径保留在 metadata 中
                # 这样 embedding 向量不会被 Header 文本污染，语义检索更精准
                if needs_secondary:
                    child_docs = self.secondary_split(section.page_content, parent_metadata, parent_id)
                    child_chunks.extend(child_docs)
                else:
                    child_doc = Document(
                        page_content=section.page_content,
                        metadata={
                            **parent_metadata,
                            'parent_chunk_id': parent_id,
                            'sub_chunk_index': 0,
                            'chunk_type': 'child'
                        }
                    )
                    # 提取关键词
                    keywords = self.extract_keywords(section.page_content)
                    if keywords:
                        child_doc.metadata['keywords'] = keywords
                    child_chunks.append(child_doc)

        logger.info(f"分块完成：{len(parent_chunks)} 个父块，{len(child_chunks)} 个子块")
        return parent_chunks, child_chunks

    def _merge_small_chunks(self, chunks: List[str], min_ratio: float = 0.3) -> List[str]:
        """
        合并过小的末尾块

        Args:
            chunks: 分块列表
            min_ratio: 最小块比例阈值（相对于chunk_size）

        Returns:
            合并后的分块列表
        """
        if len(chunks) <= 1:
            return chunks

        min_size = int(self.chunk_size * min_ratio)

        # 检查最后一个块是否过小
        if len(chunks[-1]) < min_size:
            # 合并到最后第二个块
            merged = chunks[:-2] + [chunks[-2] + '\n' + chunks[-1]]
            return merged

        return chunks
