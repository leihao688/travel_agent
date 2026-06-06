import sys
import asyncio
import contextvars
from typing import Generator, AsyncGenerator
from langchain.agents import create_agent

from agent.tools.mcp_client import mcp_tool_manager
# 确保从 middleware 导入 context 变量
from agent.tools.middleware import monitor_tool_call, log_before_model, current_agent_name
from models.factor import chat_model, create_chat_model
from utils.logger_tool import get_logger
from utils.prompt_load import weather_prompts_load

"""
使用langchain-mcp-adapters 返回的工具是纯异步的，
而 create_agent 默认尝试同步调用，导致 StructuredTool does not support sync invocation。
"""

log = get_logger(__name__)

class WeatherQueryAgent:
    """天气查询代理"""

    # 由于 __init__ 方法不能是 async 的，我们将工具的加载和 Agent 的创建推迟到 get_stream 执行时（懒加载）。
    def __init__(self):
        pass

    async def get_stream(self, query: str) -> AsyncGenerator[str, None]:
        """异步流式调用"""
        token = current_agent_name.set("WeatherQueryAgent")
        try:
            # weather_agent_prompt.txt. 异步等待工具加载（仅在第一次执行时连接 MCP Server）

            try:
                tools = await mcp_tool_manager.get_tools()
                log.info(f"[WeatherQueryAgent] 成功加载 {len(tools)} 个MCP工具")
            except Exception as e:
                log.error(f"[WeatherQueryAgent] MCP工具加载失败: {e}")
                yield f"❌ 天气服务暂时不可用，请稍后重试"
                return
            agent = create_agent(
                model=create_chat_model(),
                tools=tools,
                system_prompt=weather_prompts_load(),
                middleware=[monitor_tool_call, log_before_model]
            )

            try:
                async for chunk, metadata in agent.astream(
                        {"messages": [{"role": "user", "content": query}]},
                        stream_mode="messages",
                        config={"recursion_limit": 15}
                ):

                    if hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, str) and content.strip():
                            yield content

            except Exception as e:
                log.error(f"[WeatherQueryAgent] Agent执行失败: {type(e).__name__}: {str(e)}")
                yield f"❌ 天气查询失败: {str(e)}"

            except Exception as e:
                log.error(f"[WeatherQueryAgent] 未预期的错误: {type(e).__name__}: {str(e)}")
                yield f"❌ 系统错误: {str(e)}"

        finally:
            current_agent_name.reset(token)


if __name__ == "__main__":
    # 🔥 核心修改：使用 asyncio.run() 运行异步测试
    async def run_test():
        agent = WeatherQueryAgent()
        print("\n=== 异步流式输出测试 ===\n")
        async for token in agent.get_stream("福州明天的天气如何"):
            sys.stdout.write(token)
            sys.stdout.flush()
        print("\n=== 输出结束 ===\n")


    asyncio.run(run_test())
