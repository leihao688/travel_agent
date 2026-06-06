"""
MCP 工具管理器 - 供所有子 Agent 复用
支持懒加载、全局单例和多服务器配置
支持从魔搭社区接入远程 MCP 服务
"""
import os
import sys

# --- UTF-8 编码修复（必须在其他导入之前） ---
os.environ['PYTHONUTF8'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'zh_CN.UTF-8'
os.environ['LC_ALL'] = 'zh_CN.UTF-8'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import asyncio
import traceback
from typing import List, Dict
from langchain_core.tools import BaseTool
from dotenv import load_dotenv

# 确保加载 .env 文件
load_dotenv()

from utils.logger_tool import get_logger

log = get_logger(__name__)

# 本地 MCP 服务配置
LOCAL_MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8081/mcp")

# 高德地图 MCP 服务配置（从环境变量读取）
GAODE_MCP_URL = os.getenv("GAODE_MCP_URL", "")
GAODE_MCP_API_KEY = os.getenv("GAODE_MCP_API_KEY", "")

# 今天吃什么 MCP 服务配置
HOWTOCOOK_MCP_URL = os.getenv("HOWTOCOOK_MCP_URL", "")
HOWTOCOOK_MCP_API_KEY = os.getenv("HOWTOCOOK_MCP_API_KEY", "")

# 必应搜索 MCP 服务配置
BING_MCP_URL = os.getenv("BING_MCP_URL", "")
BING_MCP_API_KEY = os.getenv("BING_MCP_API_KEY", "")

# 图像生成 MCP 服务配置
IMAGE_GEN_MCP_URL = os.getenv("IMAGE_GEN_MCP_URL", "")
IMAGE_GEN_MCP_API_KEY = os.getenv("IMAGE_GEN_MCP_API_KEY", "")

# ChatPPT MCP 服务配置
CHATPPT_MCP_URL = os.getenv("CHATPPT_MCP_URL", "")
CHATPPT_MCP_API_KEY = os.getenv("CHATPPT_MCP_API_KEY", "")

# 12306 查票 MCP 服务配置
TICKET_12306_MCP_URL = os.getenv("TICKET_12306_MCP_URL", "")
TICKET_12306_MCP_API_KEY = os.getenv("TICKET_12306_MCP_API_KEY", "")

# Fetch MCP 服务配置
FETCH_MCP_URL = os.getenv("FETCH_MCP_URL", "")
FETCH_MCP_API_KEY = os.getenv("FETCH_MCP_API_KEY", "")



# 调试：打印环境变量值
log.info(f"[MCPToolManager] 环境变量检查:")
log.info(f"  - GAODE_MCP_URL: {'已配置' if GAODE_MCP_URL else '未配置'}")
log.info(f"  - GAODE_MCP_API_KEY: {'已配置' if GAODE_MCP_API_KEY else '未配置'}")
log.info(f"  - HOWTOCOOK_MCP_URL: {'已配置' if HOWTOCOOK_MCP_URL else '未配置'}")
log.info(f"  - HOWTOCOOK_MCP_API_KEY: {'已配置' if HOWTOCOOK_MCP_API_KEY else '未配置'}")
log.info(f"  - BING_MCP_URL: {'已配置' if BING_MCP_URL else '未配置'}")
log.info(f"  - BING_MCP_API_KEY: {'已配置' if BING_MCP_API_KEY else '未配置'}")
log.info(f"  - IMAGE_GEN_MCP_URL: {'已配置' if IMAGE_GEN_MCP_URL else '未配置'}")
log.info(f"  - IMAGE_GEN_MCP_API_KEY: {'已配置' if IMAGE_GEN_MCP_API_KEY else '未配置'}")
log.info(f"  - CHATPPT_MCP_URL: {'已配置' if CHATPPT_MCP_URL else '未配置'}")
log.info(f"  - CHATPPT_MCP_API_KEY: {'已配置' if CHATPPT_MCP_API_KEY else '未配置'}")
log.info(f"  - TICKET_12306_MCP_URL: {'已配置' if TICKET_12306_MCP_URL else '未配置'}")
log.info(f"  - TICKET_12306_MCP_API_KEY: {'已配置' if TICKET_12306_MCP_API_KEY else '未配置'}")
log.info(f"  - FETCH_MCP_URL: {'已配置' if FETCH_MCP_URL else '未配置'}")
log.info(f"  - FETCH_MCP_API_KEY: {'已配置' if FETCH_MCP_API_KEY else '未配置'}")


class MCPToolManager:
    """MCP 工具管理器 - 单例模式"""

    _instance = None
    _tools = None
    _loading_lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._loading_lock = asyncio.Lock()
        return cls._instance

    async def get_tools(self) -> List[BaseTool]:
        """获取 MCP 工具列表（懒加载）"""
        async with self._loading_lock:
            if self._tools is None:
                self._tools = await self._load_tools()
            return self._tools

    @staticmethod
    async def _load_tools() -> List[BaseTool]:
        """从多个 MCP Server 加载工具（本地 + 远程魔搭）"""
        from langchain_mcp_adapters.client import MultiServerMCPClient

        try:
            # 1. 构建服务器配置字典
            servers: Dict[str, dict] = {}

            # 添加本地 MCP 服务
            servers["local_travel_agent"] = {
                "transport": "streamable_http",
                "url": LOCAL_MCP_URL
            }
            log.info(f"[MCPToolManager] 已配置本地 MCP 服务: {LOCAL_MCP_URL}")

            # 添加高德地图 MCP 服务（如果配置了URL）
            if GAODE_MCP_URL:
                # 调试：检查 URL 是否包含非 ASCII 字符
                try:
                    GAODE_MCP_URL.encode('ascii')
                    log.info(f"[MCPToolManager] 高德地图 URL 是纯 ASCII")
                except UnicodeEncodeError as e:
                    log.error(f"[MCPToolManager] 高德地图 URL 包含非 ASCII 字符: {e}")

                server_config = {
                    "transport": "streamable_http",
                    "url": GAODE_MCP_URL
                }
                # 如果有 API Key，添加认证头；否则不需要
                if GAODE_MCP_API_KEY and GAODE_MCP_API_KEY.strip():
                    server_config["headers"] = {
                        "Authorization": f"Bearer {GAODE_MCP_API_KEY}",
                        "Content-Type": "application/json"
                    }
                servers["gaode_maps"] = server_config
                log.info(f"[MCPToolManager] 已配置高德地图 MCP 服务: {GAODE_MCP_URL}")

            # 添加今天吃什么服务
            if HOWTOCOOK_MCP_URL:
                try:
                    HOWTOCOOK_MCP_URL.encode('ascii')
                    log.info(f"[MCPToolManager] 今天吃什么 URL 是纯 ASCII")
                except UnicodeEncodeError as e:
                    log.error(f"[MCPToolManager] 今天吃什么 URL 包含非 ASCII 字符: {e}")

                server_config_2 = {
                    "transport": "streamable_http",
                    "url": HOWTOCOOK_MCP_URL
                }
                if HOWTOCOOK_MCP_API_KEY and HOWTOCOOK_MCP_API_KEY.strip():
                    server_config_2["headers"] = {
                        "Authorization": f"Bearer {HOWTOCOOK_MCP_API_KEY}",
                        "Content-Type": "application/json"
                    }
                servers["howtocook"] = server_config_2
                log.info(f"[MCPToolManager] 已配置今天吃什么 MCP 服务: {HOWTOCOOK_MCP_URL}")

            # 添加必应搜索服务
            if BING_MCP_URL:
                try:
                    BING_MCP_URL.encode('ascii')
                    log.info(f"[MCPToolManager] 必应搜索 URL 是纯 ASCII")
                except UnicodeEncodeError as e:
                    log.error(f"[MCPToolManager] 必应搜索 URL 包含非 ASCII 字符: {e}")

                server_config_3 = {
                    "transport": "streamable_http",
                    "url": BING_MCP_URL
                }
                if BING_MCP_API_KEY and BING_MCP_API_KEY.strip():
                    server_config_3["headers"] = {
                        "Authorization": f"Bearer {BING_MCP_API_KEY}",
                        "Content-Type": "application/json"
                    }
                servers["bing_search"] = server_config_3
                log.info(f"[MCPToolManager] 已配置必应搜索 MCP 服务: {BING_MCP_URL}")

            # 添加图像生成服务
            if IMAGE_GEN_MCP_URL:
                try:
                    IMAGE_GEN_MCP_URL.encode('ascii')
                    log.info(f"[MCPToolManager] 图像生成 URL 是纯 ASCII")
                except UnicodeEncodeError as e:
                    log.error(f"[MCPToolManager] 图像生成 URL 包含非 ASCII 字符: {e}")

                server_config_4 = {
                    "transport": "streamable_http",
                    "url": IMAGE_GEN_MCP_URL
                }
                if IMAGE_GEN_MCP_API_KEY and IMAGE_GEN_MCP_API_KEY.strip():
                    server_config_4["headers"] = {
                        "Authorization": f"Bearer {IMAGE_GEN_MCP_API_KEY}",
                        "Content-Type": "application/json"
                    }
                servers["image_generation"] = server_config_4
                log.info(f"[MCPToolManager] 已配置图像生成 MCP 服务: {IMAGE_GEN_MCP_URL}")

            # 添加 ChatPPT 服务
            if CHATPPT_MCP_URL:
                try:
                    CHATPPT_MCP_URL.encode('ascii')
                    log.info(f"[MCPToolManager] ChatPPT URL 是纯 ASCII")
                except UnicodeEncodeError as e:
                    log.error(f"[MCPToolManager] ChatPPT URL 包含非 ASCII 字符: {e}")

                server_config_5 = {
                    "transport": "streamable_http",
                    "url": CHATPPT_MCP_URL
                }
                if CHATPPT_MCP_API_KEY and CHATPPT_MCP_API_KEY.strip():
                    server_config_5["headers"] = {
                        "Authorization": f"Bearer {CHATPPT_MCP_API_KEY}",
                        "Content-Type": "application/json"
                    }
                servers["chatppt"] = server_config_5
                log.info(f"[MCPToolManager] 已配置 ChatPPT MCP 服务: {CHATPPT_MCP_URL}")

            # 添加 12306 查票服务
            if TICKET_12306_MCP_URL:
                try:
                    TICKET_12306_MCP_URL.encode('ascii')
                    log.info(f"[MCPToolManager] 12306 查票 URL 是纯 ASCII")
                except UnicodeEncodeError as e:
                    log.error(f"[MCPToolManager] 12306 查票 URL 包含非 ASCII 字符: {e}")

                server_config_6 = {
                    "transport": "streamable_http",
                    "url": TICKET_12306_MCP_URL
                }
                if TICKET_12306_MCP_API_KEY and TICKET_12306_MCP_API_KEY.strip():
                    server_config_6["headers"] = {
                        "Authorization": f"Bearer {TICKET_12306_MCP_API_KEY}",
                        "Content-Type": "application/json"
                    }
                servers["ticket_12306"] = server_config_6
                log.info(f"[MCPToolManager] 已配置 12306 查票 MCP 服务: {TICKET_12306_MCP_URL}")

            # 添加 Fetch 服务
            if FETCH_MCP_URL:
                try:
                    FETCH_MCP_URL.encode('ascii')
                    log.info(f"[MCPToolManager] Fetch URL 是纯 ASCII")
                except UnicodeEncodeError as e:
                    log.error(f"[MCPToolManager] Fetch URL 包含非 ASCII 字符: {e}")

                server_config_7 = {
                    "transport": "streamable_http",
                    "url": FETCH_MCP_URL
                }
                if FETCH_MCP_API_KEY and FETCH_MCP_API_KEY.strip():
                    server_config_7["headers"] = {
                        "Authorization": f"Bearer {FETCH_MCP_API_KEY}",
                        "Content-Type": "application/json"
                    }
                servers["fetch"] = server_config_7
                log.info(f"[MCPToolManager] 已配置 Fetch MCP 服务: {FETCH_MCP_URL}")

            if not servers:
                raise ValueError("未配置任何 MCP 服务器")

            # 2. 创建多服务器客户端
            client = MultiServerMCPClient(servers)

            # 3. 加载所有工具（添加异常处理绕过 langchain-mcp-adapters 的 bug）
            try:
                raw_tools = await client.get_tools()
            except UnboundLocalError as e:
                # langchain-mcp-adapters 库的 bug：当某个服务器连接失败时会抛出 UnboundLocalError
                log.warning(f"[MCPToolManager] langchain-mcp-adapters internal error: {str(e)}")
                log.warning(f"[MCPToolManager] Some servers failed to load. Returning available tools.")
                raw_tools = []  # 返回空列表，继续使用其他可用的工具
            except ExceptionGroup as eg:
                # 当某个服务器连接失败时会抛出 ExceptionGroup
                log.warning(f"[MCPToolManager] ExceptionGroup: Some servers failed to connect")
                log.warning(f"[MCPToolManager] Number of errors: {len(eg.exceptions)}")
                # 尝试逐个加载服务器
                raw_tools = []
                for server_name, server_config in servers.items():
                    try:
                        single_client = MultiServerMCPClient({server_name: server_config})
                        tools = await single_client.get_tools()
                        raw_tools.extend(tools)
                        log.info(f"[MCPToolManager] 成功加载 {server_name} 的 {len(tools)} 个工具")
                    except Exception as e:
                        log.warning(f"[MCPToolManager] 加载 {server_name} 失败: {str(e)[:50]}")
                if raw_tools:
                    log.info(f"[MCPToolManager] 共成功加载 {len(raw_tools)} 个工具")
                else:
                    log.warning(f"[MCPToolManager] 所有服务器都加载失败")

            return raw_tools

        except Exception as e:
            # 使用 try-except 处理编码问题
            try:
                error_msg = f"{type(e).__name__}: {str(e)}"
            except UnicodeEncodeError:
                error_msg = f"{type(e).__name__}: Encoding error"
            log.error(f"[MCPToolManager] Failed to load MCP tools: {error_msg}")
            log.error(f"[MCPToolManager] Full traceback:\n{traceback.format_exc()}")
            # 如果远程服务失败，尝试只加载本地服务
            log.info("[MCPToolManager] Trying to load local MCP service only...")
            try:
                client = MultiServerMCPClient({
                    "local_travel_agent": {
                        "transport": "streamable_http",
                        "url": LOCAL_MCP_URL
                    }
                })
                raw_tools = await client.get_tools()
                log.info(f"[MCPToolManager] 成功加载本地服务的 {len(raw_tools)} 个工具")
                return raw_tools
            except Exception as local_e:
                log.error(f"[MCPToolManager] 本地服务也加载失败: {str(local_e)}")
                raise


# 全局单例
mcp_tool_manager = MCPToolManager()
