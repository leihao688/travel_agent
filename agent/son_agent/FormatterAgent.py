from models.factor import chat_model
from models.schema import FormatterValidation
from utils.logger_tool import get_logger
from utils.prompt_load import formatter_prompts_load
from typing import Generator, AsyncGenerator
import asyncio

log = get_logger(__name__)

"""
因为只是进行格式转化因此没有必要使用create_agent这种重型工具，
create_agent太重且默认机制会导致“伪流式”体验。
"""


class FormatterAgent:
    """将 JSON 行程数据格式化为 Markdown 输出（静默自检+智能修正）"""

    def __init__(self):
        self.system_prompt = formatter_prompts_load()

    @staticmethod
    async def _generate(messages: list) -> str:
        """内部生成方法：收集完整输出，不立即返回给用户"""
        full_output = ""
        async for chunk in chat_model.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                full_output += chunk.content
        return full_output.strip()

    async def get_stream(self, json_data: str) -> AsyncGenerator[str, None]:
        """将 JSON 数据转换为 Markdown 格式"""
        log.info("[FormatterAgent] 开始格式化 JSON 数据")

        # 直接使用模型流式输出，实现真正的 Token 级别流式
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": json_data}
        ]

        async for chunk in chat_model.astream(messages):
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content

        log.info("[FormatterAgent] 格式化完成")


if __name__ == '__main__':
    import json


    async def run_test():
        formatter = FormatterAgent()

        test_json = json.dumps({
            "city": "福州",
            "weather_forecast": [
                {"date": "2026-04-25", "weather": "多云", "temperature": "16~24℃", "wind": "北风 3 级"}
            ],
            "recommended_hotels": [
                {"name": "福州香格里拉大酒店", "location": "闽江畔，距三坊七巷步行 10 分钟",
                 "price_range": "800-1200 元/晚",
                 "rating": "4.7", "features": ["豪华型", "江景房"]}
            ],
            "recommended_attractions": [
                {"name": "三坊七巷", "tag": "历史", "ticket_price": "免费", "suggested_duration": "2h",
                 "opening_hours": "08:30-17:00"}
            ],
            "daily_itinerary": [
                {
                    "day": 1,
                    "schedule": [
                        {"start_time": "09:00", "end_time": "11:30", "activity": "三坊七巷", "duration": "2.5 小时",
                         "activity_type": "attraction"}
                    ],
                    "area_focus": "鼓楼区",
                    "transport_summary": "交通以步行为主",
                    "walking_distance": "约 2 公里",
                    "hotel_for_night": "福州香格里拉大酒店"
                }
            ],
            "notes": ["部分景点周一闭馆", "建议提前预约门票"]
        }, ensure_ascii=False)

        print("\n=== 异步格式化测试 ===\n")
        async for chunk in formatter.get_stream(test_json):
            print(chunk, end="", flush=True)
        print("\n=== 测试结束 ===\n")


    asyncio.run(run_test())
