"""
日志配置模块
提供统一的日志管理功能，支持控制台和文件输出
"""

import os
import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


class LogConfig:
    """
    日志配置类
    单例模式，确保全局只有一个日志配置实例
    """
    # python私有变量的命名规约
    _instance = None
    _logger = None

    def __new__(cls):
        """
        单例模式实现
        :return: LogConfig实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        初始化日志配置
        只在第一次创建实例时执行
        """
        # 避免重复初始化
        if self._logger is not None:
            return

        # 日志基础配置
        self.log_level = logging.DEBUG  # 日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
        self.log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        self.date_format = '%Y-%m-%d %H:%M:%S'

        # 日志文件配置
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        self.log_file_prefix = 'app'
        self.max_bytes = 10 * 1024 * 1024  # 单个日志文件最大大小：10MB
        self.backup_count = 5  # 保留的备份文件数量

        # 创建日志目录
        self._create_log_dir()

        # 初始化logger
        self._setup_logger()

    def _create_log_dir(self):
        """
        创建日志目录（如果不存在）
        """
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _setup_logger(self):
        """
        配置日志记录器
        包含控制台输出和文件输出两个处理器
        """
        # 创建logger实例
        self._logger = logging.getLogger('AgentProject')
        self._logger.setLevel(self.log_level)

        # 创建日志格式器
        formatter = logging.Formatter(self.log_format, self.date_format)

        # 添加控制台处理器
        console_handler = self._create_console_handler(formatter)
        self._logger.addHandler(console_handler)

        # 添加文件处理器（按大小轮转）
        file_handler = self._create_file_handler(formatter)
        self._logger.addHandler(file_handler)

        # 添加错误日志文件处理器（只记录ERROR及以上级别）
        error_handler = self._create_error_handler(formatter)
        self._logger.addHandler(error_handler)


    def _create_console_handler(self, formatter):
        """
        创建控制台日志处理器
        :param formatter: 日志格式器
        :return: 控制台处理器
        """
        # 核心修改：将日志输出到标准错误流 (sys.stderr)，与 print 的标准输出流 (sys.stdout) 物理隔离
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)  # 控制台输出DEBUG及以上级别
        console_handler.setFormatter(formatter)
        return console_handler

    def _create_file_handler(self, formatter):
        """
        创建文件日志处理器（按大小轮转）
        :param formatter: 日志格式器
        :return: 文件处理器
        """
        # 生成日志文件名（包含日期）
        current_date = datetime.now().strftime('%Y%m%d')
        log_file_name = f"{self.log_file_prefix}_{current_date}.log"
        log_file_path = os.path.join(self.log_dir, log_file_name)

        # 使用RotatingFileHandler实现按大小轮转
        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=self.max_bytes,  # 单个文件最大字节数
            backupCount=self.backup_count,  # 保留的备份文件数
            encoding='utf-8'  # 文件编码
        )
        file_handler.setLevel(logging.DEBUG)  # 文件记录DEBUG及以上级别
        file_handler.setFormatter(formatter)
        return file_handler

    def _create_error_handler(self, formatter):
        """
        创建错误日志文件处理器（只记录ERROR及以上级别）
        :param formatter: 日志格式器
        :return: 错误日志处理器
        """
        # 生成错误日志文件名
        current_date = datetime.now().strftime('%Y%m%d')
        error_log_file_name = f"error_{current_date}.log"
        error_log_file_path = os.path.join(self.log_dir, error_log_file_name)

        # 使用TimedRotatingFileHandler实现按天轮转
        error_handler = TimedRotatingFileHandler(
            filename=error_log_file_path,
            when='midnight',  # 每天午夜轮转
            interval=1,  # 每1天轮转一次
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)  # 只记录ERROR及以上级别
        error_handler.setFormatter(formatter)
        return error_handler

    @property
    def logger(self):
        """
        获取logger实例
        :return: logging.Logger实例
        """
        return self._logger

    def set_level(self, level):
        """
        动态设置日志级别
        :param level: 日志级别（logging.DEBUG, logging.INFO等）
        """
        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)

    def get_logger(self, name=None):
        """
        获取指定名称的logger实例
        :param name: logger名称，默认为None时使用根logger
        :return: logging.Logger实例
        """
        if name:
            return logging.getLogger(f'AgentProject.{name}')
        return self._logger


def get_logger(name=None):
    """
    便捷函数：获取logger实例
    :param name: logger名称（通常是模块名，使用__name__）
    :return: logging.Logger实例

    使用示例：
        logger = get_logger(__name__)
        logger.info("这是一条信息日志")
        logger.error("这是一条错误日志")
    """
    log_config = LogConfig()
    return log_config.get_logger(name)


# 测试代码
if __name__ == '__main__':
    # 获取logger实例
    logger = get_logger(__name__)

    # 测试不同级别的日志
    logger.debug("这是一条调试日志")
    logger.info("这是一条信息日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    logger.critical("这是一条严重错误日志")

    print(f"日志文件保存在: {LogConfig().log_dir}")
