import hashlib

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_core.documents import Document
import os
from utils.logger_tool import LogConfig
from utils.path_handle import get_absolute_path_with_base, get_project_root

log = LogConfig()
logger = log.get_logger(__name__)


def text_loader(file_path: str, passwd: str = None) -> list[Document]:
    return TextLoader(file_path, "utf-8").load()


def pdf_loader(file_path: str, passwd: str = None) -> list[Document]:
    return PyPDFLoader(file_path).load()


def listdir_with_allowed_type(path: str, allowed_type: tuple[str]):
    files = []
    if not os.path.isdir(path):
        logger.error(f"{path}不是有效的文件夹")
        return []

    for root, dirs, filenames in os.walk(path):
        for filename in filenames:
            if filename.endswith(allowed_type):
                files.append(os.path.join(root, filename))
    return tuple(files)


def get_file_md5_hex(file_path: str):
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return
    if not os.path.isfile(file_path):
        logger.error(f"不是文件: {file_path}")
        return
    md5_obj = hashlib.md5()
    chunk_size = 4096
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
        return md5_obj.hexdigest()

    except Exception as e:
        logger.error(f"获取文件MD5失败: {file_path}")
        logger.error(e)
        return None


def file_loader(file_path: str):
    if file_path.endswith("txt"):
        return text_loader(file_path)
    if file_path.endswith("pdf"):
        return pdf_loader(file_path)
    if file_path.endswith("md"):
        return text_loader(file_path)
