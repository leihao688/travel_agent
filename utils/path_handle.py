import os
from pathlib import Path

from utils.config_load import chorma_config


def get_absolute_path(relative_path: str) -> str:
    """
    获取文件或目录的绝对路径

    Args:
        relative_path: 相对路径字符串

    Returns:
        绝对路径字符串
    """
    return str(Path(relative_path).resolve())


def get_project_root() -> str:
    """
    获取项目根目录的绝对路径

    Returns:
        项目根目录的绝对路径
    """
    return str(Path(__file__).parent.parent.resolve())


def get_absolute_path_with_base(base_path: str, relative_path: str) -> str:
    """
    基于指定基础路径获取绝对路径

    Args:
        base_path: 基础路径
        relative_path: 相对于基础路径的路径

    Returns:
        完整的绝对路径字符串
    """
    return str(Path(base_path) / relative_path)


if __name__ == '__main__':
    print(get_absolute_path_with_base(get_project_root(),chorma_config["persist_directory"]))
