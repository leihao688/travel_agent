"""
Skill 初始化器 - 在应用启动时注册所有 Skill
"""
import asyncio
from agent.tools.mcp_client import mcp_tool_manager
from agent.skills.skill_registry import Skill, skill_registry
from utils.logger_tool import get_logger
from utils.prompt_load import main_prompts_load

log = get_logger(__name__)


async def initialize_skills():
    """初始化并注册所有 Skill"""
    log.info("[SkillInitializer] 开始加载 Skills...")

    # 🔥 先加载 MCP 工具
    all_tools = await mcp_tool_manager.get_tools()
    log.info(f"[SkillInitializer] 已加载 {len(all_tools)} 个 MCP 工具")

    # 🔥 从工具列表中按名称提取子集
    tool_map = {tool.name: tool for tool in all_tools}
    #  工具缺失告警
    for tool_name in ["query_weather", "search_map_poi", "rag_check", "baidu_search", "get_route_info"]:
        if tool_name not in tool_map:
            log.warning(f"[SkillInitializer] MCP 工具缺失: {tool_name}")

    # ==================== 1. 天气查询 Skill ====================
    weather_skill = Skill(
        name="weather",
        triggers=["/weather", "查天气", "天气怎么样", "今天天气", "天气如何", "气温", "天气预报"],
        prompt="""你是一个专业的天气查询助手。

### 职责
- 只负责查询天气信息
- 不要提供旅行规划、景点推荐等其他信息

### 输出格式
直接返回天气查询结果，保持简洁明了。""",
        tools=[tool_map.get("query_weather")] if "query_weather" in tool_map else [],
        description="查询城市天气信息",
        priority=10,  # 较高优先级
        examples=[
            "北京今天天气怎么样？",
            "明天上海会下雨吗？",
            "查一下广州的气温"
        ]
    )
    skill_registry.register(weather_skill)

    # ==================== 2. 酒店推荐 Skill ====================
    hotel_skill = Skill(
        name="hotel",
        triggers=["/hotel",  "订酒店", "酒店", "住宿", "宾馆", "民宿", "住哪里", "找个住的地方"],
        prompt="""你是一个专业的酒店推荐助手。

### 职责
- 只负责推荐酒店住宿
- 根据用户预算、位置偏好推荐合适的酒店
- 不要提供行程规划、景点推荐等其他信息

### 输出格式
以清晰的列表形式展示推荐的酒店，包含名称、位置、价格、特色等信息。""",
        tools=[tool_map.get("search_map_poi")] if "search_map_poi" in tool_map else [],
        description="推荐城市酒店住宿",
        priority=10,
        examples=[
            "推荐几家北京三里屯附近的酒店",
            "我想找上海外滩附近的经济型酒店",
            "成都春熙路有什么好的民宿？"
        ]
    )
    skill_registry.register(hotel_skill)

    # ==================== 3. 景点查询 Skill ====================
    attraction_skill = Skill(
        name="attraction",
        triggers=["/attraction", "景点推荐", "有什么好玩的", "旅游景点"],
        prompt="""你是一个专业的景点推荐助手。

### 职责
- 只负责推荐旅游景点
- 根据用户兴趣、时间安排推荐合适的景点
- 不要提供酒店、交通等其他信息

### 输出格式
以清晰的列表形式展示推荐的景点，包含名称、类型、门票、开放时间等信息。""",
        tools=[tool_map.get("search_map_poi")] if "search_map_poi" in tool_map else [],
        description="查询城市旅游景点",
        priority=10,
        examples=[
            "北京有哪些必去的景点？",
            "推荐几个西安的历史景点",
            "杭州有什么好玩的地方？"
        ]

    )
    skill_registry.register(attraction_skill)

    # ==================== 4. 完整行程规划 Skill（默认） ====================
    # 🔥 为 plan Skill 筛选旅行规划相关工具，保留子 Agent 实现并行查询
    # 注意：内部子 Agent 工具（query_weather, search_attractions 等）由 MainAgent._get_tools() 提供
    # 这里只添加 MCP 补充工具
    plan_mcp_tools = [
        # === MCP 工具（补充能力）===
        tool_map.get("maps_weather"),
        tool_map.get("maps_text_search"),
        tool_map.get("maps_around_search"),
        tool_map.get("maps_direction_driving"),
        tool_map.get("maps_direction_walking"),
        tool_map.get("maps_direction_transit_integrated"),
        tool_map.get("maps_distance"),
        tool_map.get("maps_geo"),
        tool_map.get("maps_regeocode"),
        # 火车票查询
        tool_map.get("ticket_12306"),
        # RAG 知识库
        tool_map.get("rag_check"),
    ]
    # 过滤掉 None
    plan_mcp_tools = [t for t in plan_mcp_tools if t is not None]

    plan_skill = Skill(
        name="plan",
        triggers=["/plan",  "帮我规划", "行程安排", "旅行计划", "我想去", "旅游攻略", "做攻略", "去旅游", "去旅行", "旅行", "旅游"],
        prompt=main_prompts_load(),
        tools=plan_mcp_tools,  # MCP 补充工具（内部子 Agent 工具由 MainAgent 自动添加）
        description="完整旅行行程规划",
        priority=5,  #  中等优先级（低于具体技能）
        examples=[
            "帮我规划北京三日游",
            "我想去三亚玩两天，预算中等",
            "制定一个成都五天的旅行计划",
            "查一下上海到北京的火车票，然后规划行程"
        ]
    )
    skill_registry.register(plan_skill)

    # ==================== 5. 通用 Skill（默认 Fallback） ====================
    chat_skill = Skill(
        name="chat",
        triggers=[""],  # 空触发词，作为默认 Fallback
        prompt="""你是一个全能的智能助手，可以处理各种类型的请求。

### 职责
- 回答用户的任何问题
- 根据问题类型自动选择合适的工具
- 提供准确、有用的信息

### 可用工具
- 天气查询：`query_weather`
- 地图搜索：`search_map_poi`, `maps_text_search`, `maps_around_search`
- 路径规划：`get_route_info`, `maps_direction_driving`, `maps_direction_walking`
- 美食推荐：`mcp_howtocook_whatToEat`, `mcp_howtocook_recommendMeals`
- 网页搜索：`bing_search`, `baidu_search`
- 图像生成：`text_to_image`, `text_image_to_image`
- RAG 知识库：`rag_check`

- **火车票查询：12306 查票工具**（查询火车票余票、时刻表等）

### 工具选择原则
1. 天气相关 → 使用天气查询工具
2. 地点/景点/酒店 → 使用地图搜索工具
3. 路线/导航 → 使用路径规划工具
4. 美食/菜谱 → 使用美食推荐工具
5. 信息搜索 → 使用网页搜索工具
6. 图片生成 → 使用图像生成工具
7. 旅行知识 → 使用 RAG 知识库
8. **火车票查询 → 使用 12306 查票工具**

### 注意
- 灵活使用工具，不要局限于特定类型
- 如果用户问题不明确，可以追问澄清
- 保持回复简洁友好""",
        tools=all_tools,  # 使用全部工具
        description="通用智能助手，处理各类请求",
        priority=1,  # 最低优先级，作为 Fallback
        examples=[
            "你好，帮我查一下北京天气",
            "今晚吃什么好？",
            "帮我搜索杭州旅游攻略",
            "生成一张风景图片",
            "从故宫到颐和园怎么走？",
            "北京有哪些4A级景区？",
            "查一下明天上海到北京的高铁还有票吗？"
        ]
    )
    skill_registry.register(chat_skill)

    log.info(f"[SkillInitializer] 成功注册 {len(skill_registry.get_all_skills())} 个 Skills")
    for name, skill in skill_registry.get_all_skills().items():
        log.info(f"  - {name}: {skill.description} (触发词: {', '.join(skill.triggers[:2])}...)")


# 应用启动时调用
if __name__ == "__main__":
    asyncio.run(initialize_skills())
