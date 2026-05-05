"""
MCP 工具管理器 - 供所有子 Agent 复用
支持懒加载和全局单例
"""
import os
import asyncio
from typing import List
from langchain_core.tools import BaseTool

from utils.logger_tool import get_logger

log = get_logger(__name__)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")


class MCPToolManager:
    """MCP 工具管理器 - 单例模式"""

    _instance = None
    _tools = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_tools(self) -> List[BaseTool]:
        """获取 MCP 工具列表（懒加载）"""
        if self._tools is None:
            # 🔥 必须加 await，否则存入的是协程对象
            self._tools = await self._load_tools()
        return self._tools

    @staticmethod
    async def _load_tools() -> List[BaseTool]:
        """从 MCP Server 加载工具"""
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient({
            "travel_agent": {
                "transport": "http",
                "url": MCP_SERVER_URL
            }
        })
        raw_tools = await client.get_tools()
        # 🔥 必须加 await，等待网络请求完成
        log.info(f"=== 工具列表 ===")
        log.info(f"[MCPToolManager] 已加载 {len(raw_tools)} 个工具")
        return raw_tools


# 全局单例
mcp_tool_manager = MCPToolManager()
