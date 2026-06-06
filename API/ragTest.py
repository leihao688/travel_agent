"""
RAG 测试 API - 用于展示分块和检索效果
"""
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any
import os

from rag.ParentChunkStore import ParentChunkStore
from rag.Vector_Store import VectorStore
from rag.MarkdownSmartSplitter import MarkdownSmartSplitter, calculate_token_count
from utils.file_handle import get_file_md5_hex
from utils.path_handle import get_absolute_path_with_base, get_project_root
from utils.logger_tool import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/rag-test", tags=["RAG测试"])


class SplitTestRequest(BaseModel):
    """分块测试请求"""
    content: str
    max_parent_length: int = 500
    chunk_size: int = 300
    chunk_overlap: int = 30
    use_token_count: bool = False  # 是否使用 token 计数（默认 false，使用字符数）


class SplitTestResponse(BaseModel):
    """分块测试响应"""
    parent_count: int
    child_count: int
    parents: List[Dict[str, Any]]
    children: List[Dict[str, Any]]


class SearchTestRequest(BaseModel):
    """检索测试请求"""
    query: str
    top_k: int = 5
    enrich_parent: bool = True


class SearchResultItem(BaseModel):
    """检索结果项"""
    content: str                          # 最终使用的内容（优先父块）
    child_content: str = ""               # 子块原始内容
    parent_content: str = ""              # 父块完整内容
    content_source: str = "child_chunk"   # "parent_chunk" 或 "child_chunk"
    rrf_score: float
    metadata: Dict[str, Any]


class SearchTestResponse(BaseModel):
    """检索测试响应"""
    query: str
    results: List[SearchResultItem]
    parent_enriched: bool = False


@router.post("/split-test", response_model=SplitTestResponse)
async def test_split(request: SplitTestRequest):
    """
    测试 Markdown 分块效果
    """
    try:
        splitter = MarkdownSmartSplitter(
            max_parent_length=request.max_parent_length,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            use_token_count=request.use_token_count  # 根据前端选择
        )

        parent_chunks, child_chunks = splitter.split_text(
            request.content,
            source="test"
        )

        # 格式化父块信息
        parents = []
        for idx, parent in enumerate(parent_chunks):
            char_length = len(parent.page_content)

            parent_info = {
                "index": idx + 1,
                "char_length": char_length,
                "metadata": parent.metadata,
                "content_preview": parent.page_content[:200] + "..." if len(
                    parent.page_content) > 200 else parent.page_content
            }

            # 如果使用 token 计数，添加 token_length
            if request.use_token_count:
                token_length = calculate_token_count(parent.page_content)
                parent_info["token_length"] = token_length

            parents.append(parent_info)

        # 格式化子块信息
        children = []
        for idx, child in enumerate(child_chunks):
            char_length = len(child.page_content)

            child_info = {
                "index": idx + 1,
                "char_length": char_length,
                "has_special": child.metadata.get('has_special_structure', False),
                "special_type": child.metadata.get('special_type', ''),
                "sub_chunk_index": child.metadata.get('sub_chunk_index', 0),
                "content": child.page_content
            }

            # 如果使用 token 计数，添加 token_length
            if request.use_token_count:
                token_length = calculate_token_count(child.page_content)
                child_info["token_length"] = token_length

            children.append(child_info)

        return SplitTestResponse(
            parent_count=len(parent_chunks),
            child_count=len(child_chunks),
            parents=parents,
            children=children
        )

    except Exception as e:
        logger.error(f"分块测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-test", response_model=SearchTestResponse)
async def test_search(request: SearchTestRequest):
    """
    测试 RAG 检索效果（使用 RRF 融合）+ 可选父块回填展示
    """
    try:
        vector_store = VectorStore()
        retriever = vector_store.get_retriever()

        docs = retriever.invoke(request.query)

        # 父块回填
        parent_chunks_map = {}
        if request.enrich_parent:
            parent_chunk_ids = []
            for doc in docs:
                pid = doc.metadata.get('parent_chunk_id')
                if pid and pid not in parent_chunk_ids:
                    parent_chunk_ids.append(pid)

            if parent_chunk_ids:
                parent_store = ParentChunkStore()
                parents_data = parent_store.get_parents_by_ids(parent_chunk_ids)
                for parent in parents_data:
                    parent_chunks_map[parent['chunk_id']] = parent['full_content']

        results = []
        for doc in docs:
            parent_id = doc.metadata.get('parent_chunk_id')
            parent_full = parent_chunks_map.get(parent_id, '') if parent_id else ''

            results.append(SearchResultItem(
                content=parent_full if parent_full else doc.page_content,
                child_content=doc.page_content,
                parent_content=parent_full,
                content_source="parent_chunk" if parent_full else "child_chunk",
                rrf_score=doc.metadata.get('rrf_score', 0),
                metadata={
                    "source": doc.metadata.get('source', ''),
                    "Header_1": doc.metadata.get('Header_1', ''),
                    "Header_2": doc.metadata.get('Header_2', ''),
                    "Header_3": doc.metadata.get('Header_3', ''),
                    "has_special": doc.metadata.get('has_special_structure', False),
                    "special_type": doc.metadata.get('special_type', ''),
                    "parent_chunk_id": doc.metadata.get('parent_chunk_id', ''),
                    "keywords": doc.metadata.get('keywords', [])
                }
            ))

        return SearchTestResponse(
            query=request.query,
            results=results,
            parent_enriched=bool(parent_chunks_map)
        )

    except Exception as e:
        logger.error(f"检索测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-process")
async def upload_and_process_file(
        file: UploadFile = File(...),
        max_parent_length: int = 500,
        chunk_size: int = 300,
        chunk_overlap: int = 30,
        use_token_count: bool = False
):
    """
    上传文件并处理到知识库（父块存MySQL，子块存ChromaDB）
    """
    try:
        # 读取文件内容
        content = await file.read()
        content_str = content.decode('utf-8')

        # 临时保存文件以计算 MD5
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            file_md5 = get_file_md5_hex(tmp_path)
        finally:
            os.unlink(tmp_path)

        # 检查文件是否已存在
        parent_store = ParentChunkStore()
        session = parent_store.get_session()
        try:
            from rag.ParentChunkStore import FileProcessingLog
            existing_log = session.query(FileProcessingLog).filter(
                FileProcessingLog.file_md5 == file_md5,
                FileProcessingLog.processing_status == 'completed'
            ).first()

            if existing_log:
                return {
                    "success": False,
                    "message": f"文件已存在于知识库中",
                    "filename": file.filename,
                    "file_md5": file_md5
                }
        finally:
            session.close()

        # 创建处理日志（processing状态）
        parent_store.add_processing_log({
            'file_name': file.filename,
            'file_path': f"data/{file.filename}",
            'file_md5': file_md5,
            'processing_status': 'processing'
        })

        # 使用 MarkdownSmartSplitter 分块
        splitter = MarkdownSmartSplitter(
            max_parent_length=max_parent_length,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            use_token_count=use_token_count  # 支持 token 计数
        )

        parent_chunks, child_chunks = splitter.split_text(
            content_str,
            source=file.filename
        )

        logger.info(f"文件 {file.filename} 分割: {len(parent_chunks)} 个父块, {len(child_chunks)} 个子块")

        # 保存到向量库（子块）
        vector_store = VectorStore()

        if child_chunks:
            vector_store.vector_store.add_documents(child_chunks)
            logger.info(f"子块已存储到 ChromaDB: {len(child_chunks)} 条")

        # 保存父块到 MySQL
        parent_data_list = []

        for parent in parent_chunks:
            parent_chunk_id = parent.metadata.get('parent_chunk_id', '')
            child_count = len([
                c for c in child_chunks
                if c.metadata.get('parent_chunk_id') == parent_chunk_id
            ])

            parent_data_list.append({
                'chunk_id': parent_chunk_id,
                'file_path': file.filename,
                'file_name': file.filename,
                'file_md5': file_md5,
                'header_1': parent.metadata.get('Header_1', ''),
                'header_2': parent.metadata.get('Header_2', ''),
                'header_3': parent.metadata.get('Header_3', ''),
                'full_content': parent.page_content,
                'content_length': len(parent.page_content),
                'child_count': child_count,
                'metadata_json': '{}',
                'chunk_index': int(parent.metadata.get('chunk_index', 0)),
                'chroma_collection': 'agent'
            })

        if parent_data_list:
            parent_store.batch_add_parent_chunks(parent_data_list)
            logger.info(f"父块已存储到 MySQL: {len(parent_data_list)} 条")

        # 更新处理日志为 completed
        parent_store.add_processing_log({
            'file_name': file.filename,
            'file_path': f"data/{file.filename}",
            'file_md5': file_md5,
            'total_parent_chunks': len(parent_chunks),
            'total_child_chunks': len(child_chunks),
            'processing_status': 'completed'
        })

        return {
            "success": True,
            "message": f"文件处理成功",
            "filename": file.filename,
            "parent_count": len(parent_chunks),
            "child_count": len(child_chunks),
            "file_md5": file_md5
        }

    except Exception as e:
        logger.error(f"文件处理失败: {str(e)}")

        # 更新处理日志为 failed
        try:
            parent_store.add_processing_log({
                'file_name': file.filename,
                'file_path': f"data/{file.filename}",
                'file_md5': file_md5 if 'file_md5' in locals() else '',
                'processing_status': 'failed',
                'error_message': str(e)
            })
        except:
            pass

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-list")
async def list_processed_files():
    """列出已处理的文件"""
    try:
        parent_store = ParentChunkStore()
        session = parent_store.get_session()

        try:
            from rag.ParentChunkStore import ParentChunk
            files = session.query(
                ParentChunk.file_name,
                ParentChunk.file_md5,
                ParentChunk.created_at
            ).distinct().all()

            logger.info(f"查询到 {len(files)} 个文件记录")

            file_list = []
            for f in files:
                file_info = {
                    "filename": f[0] if f[0] else "",
                    "md5": f[1] if f[1] else "",
                    "processed_at": f[2].isoformat() if f[2] else None
                }
                file_list.append(file_info)
                logger.info(f"文件: {file_info}")

            return {
                "files": file_list
            }
        finally:
            session.close()

    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


def delete_file_md5_record(file_md5):
    """从 md5.txt 中删除指定的 MD5 记录"""
    try:
        md5_file_path = os.path.join(get_project_root(), "md5.txt")

        if not os.path.exists(md5_file_path):
            logger.warning(f"MD5 文件不存在: {md5_file_path}")
            return

        # 读取所有 MD5 记录
        with open(md5_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 过滤掉要删除的 MD5
        new_lines = [line for line in lines if line.strip() != file_md5]

        # 写回文件
        with open(md5_file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        logger.info(f"已从 md5.txt 删除 MD5: {file_md5}")

    except Exception as e:
        logger.error(f"删除 MD5 记录失败: {str(e)}")
        raise e


@router.get("/child-chunks/{parent_chunk_id}")
async def get_child_chunks(parent_chunk_id: str):
    """
    根据父块 ID 查找所有子块

    Args:
        parent_chunk_id: 父块的唯一标识符

    Returns:
        子块列表，包含内容和元数据
    """
    try:
        vector_store = VectorStore()

        # 从 ChromaDB 查询该父块的所有子块
        results = vector_store.vector_store.get(
            where={"parent_chunk_id": parent_chunk_id}
        )

        child_chunks = []
        if results['documents']:
            for i, doc_content in enumerate(results['documents']):
                metadata = results['metadatas'][i] if results['metadatas'] else {}
                chunk_id = results['ids'][i] if results['ids'] else ''

                child_chunks.append({
                    'chunk_id': chunk_id,
                    'content': doc_content,
                    'metadata': {
                        'sub_chunk_index': metadata.get('sub_chunk_index', 0),
                        'keywords': metadata.get('keywords', []),
                        'has_special_structure': metadata.get('has_special_structure', False),
                        'special_type': metadata.get('special_type', ''),
                        'Header_1': metadata.get('Header_1', ''),
                        'Header_2': metadata.get('Header_2', ''),
                        'Header_3': metadata.get('Header_3', ''),
                        'source': metadata.get('source', '')
                    }
                })

            # 按 sub_chunk_index 排序
            child_chunks.sort(key=lambda x: x['metadata']['sub_chunk_index'])

        logger.info(f"找到父块 {parent_chunk_id} 的 {len(child_chunks)} 个子块")

        return {
            "success": True,
            "parent_chunk_id": parent_chunk_id,
            "child_count": len(child_chunks),
            "children": child_chunks
        }

    except Exception as e:
        logger.error(f"查找子块失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete-file/{filename}")
async def delete_file(filename: str):
    """删除文件相关的父块和子块"""
    try:
        # 获取文件 MD5
        parent_store = ParentChunkStore()
        session = parent_store.get_session()

        try:
            from rag.ParentChunkStore import ParentChunk, FileProcessingLog

            # 查询文件的 MD5
            file_record = session.query(ParentChunk).filter(
                ParentChunk.file_name == filename
            ).first()

            if not file_record:
                return {
                    "success": False,
                    "message": f"文件 {filename} 不存在"
                }

            file_md5 = file_record.file_md5

            # 删除 MySQL 中的父块
            parent_count = parent_store.delete_by_file(filename)

            # 删除 ChromaDB 中的子块
            vector_store = VectorStore()
            docs = vector_store.vector_store.get(
                where={"source": filename}
            )

            deleted_child_count = 0
            if docs['ids']:
                deleted_child_count = len(docs['ids'])
                vector_store.vector_store.delete(ids=docs['ids'])
                logger.info(f"从 ChromaDB 删除了 {deleted_child_count} 个子块")

            # 更新或删除处理日志
            log_records = session.query(FileProcessingLog).filter(
                FileProcessingLog.file_md5 == file_md5
            ).all()

            for log in log_records:
                session.delete(log)

            session.commit()

            # 删除 md5.txt 中的记录
            try:
                delete_file_md5_record(file_md5)
                logger.info(f"已从 md5.txt 删除 MD5 记录: {file_md5}")
            except Exception as md5_err:
                logger.warning(f"删除 MD5 记录失败（可忽略）: {str(md5_err)}")

            return {
                "success": True,
                "message": f"已删除文件 {filename}",
                "deleted_parent_count": parent_count,
                "deleted_child_count": deleted_child_count
            }
        finally:
            session.close()

    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file-parent-chunks/{filename}")
async def get_file_parent_chunks(filename: str):
    """
    根据文件名获取所有父块（从MySQL查询）

    Args:
        filename: 文件名

    Returns:
        父块列表，包含父块信息和子块数量
    """
    try:
        parent_store = ParentChunkStore()
        parents = parent_store.get_parents_by_file(filename)

        logger.info(f"查询文件 {filename} 的父块: {len(parents)} 个")

        return {
            "success": True,
            "filename": filename,
            "parent_count": len(parents),
            "parents": parents
        }

    except Exception as e:
        logger.error(f"查询文件父块失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

