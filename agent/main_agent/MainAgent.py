import asyncio

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
import json

from agent.memory.LongTermMemory import LongTermMemory
from agent.memory.SessionMemory import SessionMemory
from agent.son_agent.AttarctionAgent import AttractionAgent
from agent.son_agent.FormatterAgent import FormatterAgent
from agent.son_agent.HotelAgent import HotelAgent
from agent.son_agent.PlanAgent import PlanPlanAgent
from agent.son_agent.SelfReviewAgent import SelfReviewAgent, ContentGuardrailAgent
from agent.son_agent.WeatherQueryAgent import WeatherQueryAgent
from agent.tools.middleware import monitor_tool_call, log_before_model, current_agent_name
from models.factor import chat_model
from models.schema import WeatherQuerySchema, AttractionSearchSchema, HotelRecommendSchema, RoutePlanSchema, \
    LogicReviewSchema, ContentGuardSchema

from utils.logger_tool import get_logger
from utils.prompt_load import main_prompts_load
from rag.Rag_service import RagService

log = get_logger(__name__)


async def _collect_output(agent_instance, query: str) -> str:
    result = ""
    chunk_count = 0
    async for chunk in agent_instance.get_stream(query):
        chunk_count += 1
        # 🔥 添加类型和长度检查
        result += str(chunk)
    # 调试：检查 strip 前后的变化
    stripped = result.strip()

    return stripped


class MainAgent:
    def __init__(self):
        self.attraction_agent = AttractionAgent()
        self.weather_agent = WeatherQueryAgent()
        self.route_agent = PlanPlanAgent()
        self.hotel_agent = HotelAgent()
        self.formatter_agent = FormatterAgent()
        self.self_review_agent = SelfReviewAgent()
        self.content_guardrail_agent = ContentGuardrailAgent()
        self.agent = None
        self.long_term_memory = LongTermMemory()
        self.session_memory = SessionMemory()
        # 🔥 从配置项读取重试次数
        self.rag_service = RagService()

    async def _get_tools(self):
        return [

            StructuredTool(
                name="query_weather",
                description="查询目的地天气。行程规划前置必调工具，city为必填项。",
                args_schema=WeatherQuerySchema,
                coroutine=self._tool_query_weather
            ),
            StructuredTool(
                name="search_attractions",
                description="查询城市旅游景点，行程规划前置必调工具，city为必填项。",
                args_schema=AttractionSearchSchema,
                coroutine=self._tool_search_attractions
            ),
            StructuredTool(
                name="recommend_hotels",
                description="推荐城市酒店住宿，支持指定预算档位，city为必填项。",
                args_schema=HotelRecommendSchema,
                coroutine=self._tool_recommend_hotels
            ),
            StructuredTool(
                name="plan_route",
                description="生成完整行程路线，必须获取完天气、景点、酒店信息后再调用，禁止直接调用。",
                args_schema=RoutePlanSchema,
                coroutine=self._tool_plan_route
            ),
            # 🔥 新增：注册逻辑评审和内容护栏为工具
            StructuredTool(
                name="logic_review",
                description="首先先对用户的问题进行逻辑性检查，对行程方案进行逻辑自检，检查可行性、合理性。content: 待评审的行程内容",
                args_schema=LogicReviewSchema,
                coroutine=self._tool_self_review
            ),
            StructuredTool(
                name="content_guardrail",
                description="通过逻辑检验后，进行最后的轻量化修正。",
                args_schema=ContentGuardSchema,
                coroutine=self._content_guardrail)
        ]

    async def _tool_query_weather(self, city: str, date: str = None) -> str:
        result = await _collect_output(self.weather_agent, f"{city} {date or ''}的天气情况")
        log.info(f"[MainAgent._tool_query_weather] 返回结果: {result[:200] if result else '空'}...")
        return result

    async def _tool_search_attractions(self, city: str, days: str) -> str:
        query = f"{city}最知名的 {days * 2} 个景点和 1 个商场"
        return await _collect_output(self.attraction_agent, query)

    async def _tool_recommend_hotels(self, city: str, budget: str = "中等") -> str:
        return await _collect_output(self.hotel_agent, f"推荐{city}酒店，预算{budget}")

    async def _tool_self_review(self, content: str, user_query: str) -> str:
        """调用 SelfReviewAgent 进行逻辑评审"""
        # 🔥 构造包含用户需求的评审上下文
        review_context = f"【用户原始需求】\n{user_query}\n\n【待评审方案】\n{content}"

        is_valid, reason, suggestion = await self.self_review_agent.review(review_context)
        result = {
            "is_valid": is_valid,
            "reason": reason,
            "suggestion": suggestion
        }
        return json.dumps(result, ensure_ascii=False)

    async def _tool_plan_route(self, city: str, days: int, weather: str, attractions: str, hotels: str,
                               people_count: int = 1, budget: str = "中等") -> str:
        # 🔥 修改：尝试解析上游返回的 JSON 字符串
        #  新增：打印传入参数，用于调试
        # log.info(f"[MainAgent._tool_plan_route] 接收到的参数:")
        # log.info(f"  - city: {city}")
        # log.info(f"  - days: {days}")
        # log.info(f"  - weather (原始): {weather[:100]}...")  # 只打印前 100 字符
        # log.info(f"  - attractions (原始): {attractions[:100]}...")
        # log.info(f"  - hotels (原始): {hotels[:100]}...")
        try:
            weather_data = json.loads(weather) if weather.startswith('[') or weather.startswith('{') else []
            attractions_data = json.loads(attractions) if attractions.startswith('[') else []
            hotels_data = json.loads(hotels) if hotels.startswith('[') else []
        except json.JSONDecodeError:
            # 兜底兼容：如果不是 JSON，保持原始字符串
            weather_data = weather
            attractions_data = attractions
            hotels_data = hotels

        # 🔥 构造结构化 JSON 传递给 PlanAgent
        context = json.dumps({
            "city": city,
            "days": days,
            "people_count": people_count,
            "budget": budget,
            "weather_forecast": weather_data,
            "recommended_attractions": attractions_data,
            "recommended_hotels": hotels_data
        }, ensure_ascii=False)

        return await _collect_output(self.route_agent, context)

    async def _content_guardrail(self, content: str) -> str:
        return await self.content_guardrail_agent.guard(content)

    # 通用逻辑自省评审（无硬编码、全自动识别所有逻辑问题）

    async def get_stream(self, query: str, session_id: str = "default", user_id: str = "default"):
        token = current_agent_name.set("MainAgent")
        try:
            # 3. 检索长期记忆
            long_term_mem = self.long_term_memory.retrieve(user_id, session_id)
            # 🔥 4. 动态注入 System Prompt（加入长期记忆）

            if not self.agent:
                base_prompt = main_prompts_load()
                system_prompt = f"""{base_prompt}
    
                ### 🧠 用户长期记忆（跨会话）
                以下信息是该用户的历史偏好，请在规划行程时**严格参考**：
                {long_term_mem if long_term_mem else "无历史记忆"}
                """
                tools = await self._get_tools()
                self.agent = create_agent(
                    model=chat_model,
                    tools=tools,
                    system_prompt=system_prompt,
                    middleware=[monitor_tool_call, log_before_model]
                )
            #  2. 加载历史记忆
            history_data = self.session_memory.get_history(session_id)
            initial_messages = []
            for item in history_data:
                if item["role"] == "user":
                    initial_messages.append(HumanMessage(content=item["content"]))
                elif item["role"] == "assistant":
                    initial_messages.append(AIMessage(content=item["content"]))
            #  3. 执行 Agent（将历史 + 当前 Query 传入）
            current_messages = initial_messages + [HumanMessage(content=query)]
            result = await self.agent.ainvoke({"messages": current_messages})
            raw_output = result.get("output", "")
            if not raw_output and result.get("messages"):
                raw_output = result["messages"][-1].content
                # 🔥 4. 存入短期记忆
            self.session_memory.add_message(session_id, "user", query)
            self.session_memory.add_message(session_id, "assistant", raw_output)

            final_content = raw_output
            #  让 LLM 自主判断是否需要格式化
            # judge_prompt = f"""请判断以下内容是否为结构化的行程规划 JSON 数据（包含 daily_itinerary、recommended_attractions 等字段）。
            # 如果是 JSON 行程数据，回复 "FORMAT"；如果不是（如诗歌、问答、闲聊等），回复 "DIRECT"。

            #             待判断内容：
            #             {final_content[:500]}"""
            #             judge_response = await chat_model.ainvoke(judge_prompt)
            #             judge_result = judge_response.content.strip().upper()

            #             # 🔥 打印 FormatterAgent 前的 JSON 数据
            #             # log.info(f"[MainAgent] FormatterAgent 前的原始内容:\n{final_content}")

            #             # ✅ 合理方案：走 FormatterAgent 格式化
            #             if "FORMAT" in judge_result:
            #                 log.info("[MainAgent] LLM 判定为 JSON 行程，走 FormatterAgent 格式化")
            #                 async for chunk in self.formatter_agent.get_stream(final_content):
            #                     yield chunk
            #             else:
            #                 log.info("[MainAgent] LLM 判定为非 JSON 内容，直接输出")
            #                 yield final_content
            log.info("[MainAgent] 开始流式输出最终内容")

            messages = [
                {"role": "system", "content": "你是一个旅行助手，请直接输出以下内容，不要添加任何开场白或结束语："},
                {"role": "user", "content": final_content}
            ]

            async for chunk in chat_model.astream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content

            # 🔥 9. 触发长期记忆存储（当会话达到一定长度时）
            if len(history_data) >= 4:
                all_messages = history_data + [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": raw_output}
                ]
                await self.long_term_memory.store_summary(user_id, all_messages)


        except Exception as e:
            log.error(f"主流程全局异常: {e}")
            try:
                response = await chat_model.ainvoke(
                    f"系统遇到了一点小故障（{str(e)}）。请用幽默自然的语气向用户解释，并尝试根据'{query}'提供一些通用建议。"
                )
                yield response.content
            except:
                yield f"\n❌ 出错：{str(e)}"
        finally:
            current_agent_name.reset(token)


if __name__ == '__main__':
    async def run_test():
        main = MainAgent()

        test_cases = [
            # "请帮我规划三亚的 skiing 滑雪行程，我要体验海上滑雪。",
            # "我今天早上在北京吃烤鸭，中午要去巴黎喂鸽子，晚上回纽约看自由女神像，请安排航班。",
            # "我要在福州不借助任何工具，直接从市区飞到鼓山顶上看日出。",
            # "我要去福州拜访林则徐，请安排和他共进晚餐的行程。",
            # "请在台风登陆当天安排我在平潭岛放风筝和野餐。",
            # "写一首关于旅行的诗"，
            # "故宫博物院门票多少钱，几点开门",
            # "爬黄山什么时候去最好，需要注意什么",
            "我明天后天想去三亚玩两天，预算中等，一个人"
        ]

        for query in test_cases:
            print(f"\n{'=' * 60}")
            print(f"💬 用户输入：{query}")
            print(f"{'=' * 60}")
            try:
                async for chunk in main.get_stream(query):
                    print(chunk, end="", flush=True)
            except Exception as e:
                print(f"❌ 测试崩溃: {e}")
            print("\n")


    asyncio.run(run_test())
