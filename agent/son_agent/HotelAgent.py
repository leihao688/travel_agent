import sys

from langchain.agents import create_agent

from agent.tools.mcp_client import mcp_tool_manager
from agent.tools.middleware import monitor_tool_call, log_before_model, current_agent_name
from models.factor import chat_model

from utils.prompt_load import hotel_prompts_load
from typing import Generator,AsyncGenerator
import asyncio


class HotelAgent:
    def __init__(self):
        self.agent = None

    async def get_stream(self, query: str) -> AsyncGenerator[str, None]:
        token = current_agent_name.set("HotelAgent")
        try:
            if self.agent is None:
                tools = await mcp_tool_manager.get_tools()
                self.agent = create_agent(
                    model=chat_model,
                    tools=tools,
                    system_prompt=hotel_prompts_load(),
                    middleware=[monitor_tool_call, log_before_model]
                )
            # 使用 messages 模式流式输出
            async for chunk, metadata in self.agent.astream(
                    {"messages": [{"role": "user", "content": query}]},
                    stream_mode="messages",
                    config={"recursion_limit": 15}  # 【新增】限制最大执行步数，防止死循环
            ):
                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, str) and (content.startswith("[") or content.startswith("{")):
                        yield content


        finally:
            current_agent_name.reset(token)


if __name__ == '__main__':

    async def run_test():
        agent = HotelAgent()
        print("\n=== 异步流式输出测试 ===\n")
        async for token in agent.get_stream("福州的景点"):
            sys.stdout.write(token)
            sys.stdout.flush()
        print("\n=== 输出结束 ===\n")


    asyncio.run(run_test())
