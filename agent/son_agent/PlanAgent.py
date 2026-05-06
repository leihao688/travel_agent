import sys
from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from agent.tools.mcp_client import mcp_tool_manager
from agent.tools.middleware import monitor_tool_call, log_before_model, current_agent_name
from models.factor import chat_model, create_chat_model
from utils.prompt_load import route_prompts_load
from typing import Generator, AsyncGenerator
import asyncio


class PlanPlanAgent:
    def __init__(self):
        self.agent = None

    async def get_stream(self, query: str) -> AsyncGenerator[str, None]:
        token = current_agent_name.set("RoutePlanAgent")
        try:
            if self.agent is None:
                # weather_agent_prompt.txt. 获取 MCP 工具列表
                all_mcp_tools = await mcp_tool_manager.get_tools()

                # 2. 🔥 关键：只保留 RoutePlanAgent 需要的工具
                # RoutePlanAgent 只需要：get_route_info（计算路线）和 search_map_poi（补充坐标）
                allowed_tool_names = {"get_route_info", "search_map_poi"}
                allowed_tools = [
                    t for t in all_mcp_tools
                    if t.name in allowed_tool_names
                ]
                self.agent = create_agent(
                    model=create_chat_model(),
                    tools=allowed_tools,
                    system_prompt=route_prompts_load(),
                    middleware=[monitor_tool_call, log_before_model]
                )
            # 使用 messages 模式流式输出

            async for chunk, metadata in self.agent.astream(
                    {"messages": [{"role": "user", "content": query}]},
                    stream_mode="messages",
                    config={"recursion_limit": 50}
            ):
                # 【核心修改】：过滤掉 ToolMessage（工具的原始返回数据）
                # 这样用户就看不到“公交方案：xxx"这种中间过程，只能看到 Agent 整理好的行程
                if isinstance(chunk, ToolMessage):
                    continue
                    # 使用 messages 模式流式输出
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        finally:
            current_agent_name.reset(token)


if __name__ == '__main__':
    import json


    async def run_test():
        agent = PlanPlanAgent()

        # 🔥 构造包含完整信息的测试数据
        test_data = {
            "city": "三亚",
            "days": 2,
            "weather": [
                {"date": "2026-04-29", "weather": "雷阵雨转多云", "temperature": "31/23℃", "wind": "南风 3级"}
            ],
            "hotels": [
                {
                    "name": "三亚湾红树林度假世界",
                    "location": "109.475,18.285",
                    "price_range": "中等",
                    "rating": "4.6"
                }
            ],
            "attractions": [
                {
                    "name": "天涯海角游览区",
                    "tag": "地标",
                    "price": "81元",
                    "duration": "3h",
                    "opening_hours": "08:00-18:00",
                    "location": "109.370,18.290"
                },
                {
                    "name": "南山文化旅游区",
                    "tag": "历史",
                    "price": "129元",
                    "duration": "4h",
                    "opening_hours": "08:00-17:30",
                    "location": "109.210,18.280"
                },
                {
                    "name": "亚龙湾热带天堂森林公园",
                    "tag": "自然",
                    "price": "170元",
                    "duration": "4h",
                    "opening_hours": "07:30-18:00",
                    "location": "109.630,18.250"
                }
            ]
        }

        query = f"""
        请根据以下 JSON 数据规划行程：
        {json.dumps(test_data, ensure_ascii=False)}

        要求：
        1. 必须调用 get_route_info 计算相邻景点的交通耗时。
        2. 动线要合理，不要绕路。
        3. 输出严格的 JSON 格式。
        """

        print("\n=== RoutePlanAgent 路线规划测试 ===\n")
        async for token in agent.get_stream(query):
            sys.stdout.write(token)
            sys.stdout.flush()
        print("\n=== 输出结束 ===\n")


    asyncio.run(run_test())
