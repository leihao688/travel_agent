import sys
import asyncio
from langchain.agents import create_agent
from agent.tools.mcp_client import mcp_tool_manager
from agent.tools.middleware import monitor_tool_call, log_before_model, current_agent_name
from utils.prompt_load import attraction_prompts_load, weather_prompts_load
from models.factor import chat_model, create_chat_model
from typing import Generator,AsyncGenerator


class AttractionAgent:
    def __init__(self):
        pass

    async def get_stream(self, query: str) -> AsyncGenerator[str, None]:
        token = current_agent_name.set("AttractionAgent")
        try:

            tools = await mcp_tool_manager.get_tools()
            agent = create_agent(
                model=create_chat_model(),
                tools=tools,
                system_prompt=attraction_prompts_load(),
                middleware=[monitor_tool_call, log_before_model]
            )
            # 使用 messages 模式流式输出
            async for chunk, metadata in agent.astream(
                    {"messages": [{"role": "user", "content": query}]},
                    stream_mode="messages",
                    config={"recursion_limit": 50}
            ):

                if hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, str):
                        # 1. 移除 Markdown 代码块标记
                        cleaned = content.replace("", "").strip()
                        # 2. 使用 in 匹配，兼容解释性文字
                        if "[" in cleaned or "{" in cleaned:
                            yield cleaned

        finally:
            current_agent_name.reset(token)


if __name__ == '__main__':
    async def run_test():
        agent = AttractionAgent()
        print("\n=== 异步流式输出测试 ===\n")
        async for token in agent.get_stream("我明天后天想去三亚玩两天"):
            sys.stdout.write(token)
            sys.stdout.flush()
        print("\n=== 输出结束 ===\n")


    asyncio.run(run_test())
