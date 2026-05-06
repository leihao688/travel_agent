import os

import httpx
from fastmcp import FastMCP
import json
import requests
import datetime
from dotenv import load_dotenv
from langchain_core.tools import tool
import time
import asyncio
from tenacity import stop_after_attempt, retry_if_exception_type, wait_exponential, retry

from agent.tools.rate_limter import rate_limiter
from rag.Rag_service import RagService
from utils.logger_tool import get_logger
import random
from config import settings

load_dotenv()
log = get_logger(__name__)
rag_tool = RagService()

QWEATHER_API_KEY = os.getenv("QWEATHER_API_KEY")
QWEATHER_API_HOST = os.getenv("QWEATHER_API_HOST", "devapi.qweather.com")

mcp = FastMCP(name="travel_agent")


@mcp.tool(
    description="检查知识库中是否包含与查询相关的信息。query: 用户查询内容")
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10),
       retry=retry_if_exception_type(httpx.HTTPError))
async def rag_check(query: str) -> str:
    result = await rag_tool.aget_summary(query)
    return result


@mcp.tool(
    description="查询指定城市的天气信息。city: 城市名，date: 日期（今天/明天/昨天/后天 或 YYYY-MM-DD）")
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10),
       retry=retry_if_exception_type(httpx.HTTPError))
async def query_weather(city: str, date: str = None) -> str:
    """异步天气查询（带限流+重试）"""
    # 🔥 限流保护：和风天气 QPS 限制
    await rate_limiter.acquire("qweather")
    if not QWEATHER_API_KEY:
        return "错误：未配置和风天气API Key"
    import re
    try:
        # 尝试从 RAG 获取城市编码
        rag_result = await rag_tool.aget_summary(f"{city}城市编码")
        # 提取 9 位数字编码
        match = re.search(r'\d{9}', rag_result)
        if match:
            location_id = match.group(0)
        else:
            return f"错误：无法从知识库获取{city}的城市编码，请检查 RAG 数据。"
    except Exception as e:
        return f"获取城市编码失败：{str(e)}"

    headers = {"X-QW-Api-Key": QWEATHER_API_KEY}
    target_date = None
    if date:
        today = datetime.date.today()
        if date == "今天":
            target_date = today
        elif date == "明天":
            target_date = today + datetime.timedelta(days=1)
        elif date == "昨天":
            target_date = today - datetime.timedelta(days=1)
        elif date == "后天":
            target_date = today + datetime.timedelta(days=2)
        else:
            try:
                target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return "日期格式错误，请使用 今天/明天/昨天/后天 或 YYYY-MM-DD"

    if target_date:
        url = f"https://{QWEATHER_API_HOST}/v7/weather/3d?location={location_id}&lang=zh&unit=m"
        date_str = target_date.strftime("%Y-%m-%d")
    else:
        url = f"https://{QWEATHER_API_HOST}/v7/weather/now?location={location_id}&lang=zh&unit=m"
        date_str = None

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        if data["code"] != "200":
            return f"天气查询失败，错误码：{data['code']}"

        if date_str:
            for day in data["daily"]:
                if day["fxDate"] == date_str:
                    import json
                    weather_data = [{
                        "city": city,
                        "date": date_str,
                        "weather": day['textDay'],
                        "temp": f"{day['tempMin']}~{day['tempMax']}",
                        "wind": f"{day['windDirDay']}{day['windScaleDay']}级"
                    }]
                    return json.dumps(weather_data, ensure_ascii=False)
            return f"未找到{city}{date_str}的天气预报数据"

        else:
            now = data["now"]
            import json
            weather_data = [{
                "city": city,
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "weather": now['text'],
                "temp": now['temp'],
                "wind": f"{now['windDir']}风{now['windScale']}级"
            }]
            return json.dumps(weather_data, ensure_ascii=False)
    except Exception as e:
        log.error(f"天气查询出错：{str(e)}")
        return f"天气查询异常"


@mcp.tool(
    description="调用此方法搜索指定城市的地点信息。keywords: 搜索关键词，city: 城市名，category: 类别(可选值: 'attraction景点, 'hotel酒店')")
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10),
       retry=retry_if_exception_type(httpx.HTTPError))
async def search_map_poi(keywords: str, city: str, category: str = "attraction") -> str:
    """高德地图通用地点搜索工具"""
    await rate_limiter.acquire("amap")
    AMAP_KEY = os.getenv("AMAP_API_KEY")
    if not AMAP_KEY:
        return "错误：未配置高德地图 API Key"

    type_code = "110000" if category == "attraction" else "150000"

    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "key": AMAP_KEY,
        "keywords": keywords,
        "city": city,
        "types": type_code,
        "output": "json"
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        # 🔥 修复：高德 API 成功状态码是 "1"
        if data.get("status") == "1":
            results = []
            for poi in data["pois"][:3]:
                loc = poi.get('location', '')
                # 🔥 优化：返回 JSON 格式，方便 Agent 提取 location
                info = {
                    "name": poi['name'],
                    "address": poi.get('address', ''),
                    "location": loc
                }
                if category == "hotel" and 'biz_ext' in poi and 'cost' in poi['biz_ext']:
                    info["price"] = f"{poi['biz_ext']['cost']}元"
                results.append(info)
            return json.dumps(results, ensure_ascii=False)

        return f"未找到相关{'景点' if category == 'attraction' else '酒店'}"
    except Exception as e:
        return f"搜索出错: {str(e)}"


@mcp.tool(description="使用百度千帆AI搜索查询实时信息如（景点的开放时间和景点的门票价格）")
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10),
       retry=retry_if_exception_type(httpx.HTTPError))
async def baidu_search(query: str) -> str:
    # 🔥 修改 weather_agent_prompt.txt：使用异步等待替代 time.sleep
    await asyncio.sleep(random.uniform(2.0, 4.0))
    await rate_limiter.acquire("baidu")
    url = "https://qianfan.baidubce.com/v2/ai_search/web_search"
    api_key = os.getenv('BAIDU_QIANFAN_API_KEY')
    if not api_key:
        return "错误：未配置百度千帆AI API Key"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [{"role": "user", "content": query}],
        "top_k": 3,
        "search_source": "baidu_search_v2"
    }

    try:
        # 🔥 修改 2：使用 httpx 发送 POST 请求
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

        log.info(f"百度搜索 API 调用成功")
        search_results = data.get("references", [])[:5]

        if not search_results:
            return "未获取到搜索结果"

        output = [f"正在通过百度搜索查询'{query}'的信息：\n"]
        for idx, item in enumerate(search_results, 1):
            title = item.get("title", "无标题")
            content = item.get("content", "无摘要")
            url_link = item.get("url", "")
            output.append(f"【{idx}】{title}\n摘要：{content[:400]}...\n来源：{url_link}")

        return "\n\n".join(output)

    except httpx.HTTPError as e:
        log.error(f"百度搜索失败: {e}")
        return f"搜索失败：{str(e)}"


@mcp.tool(
    description="查询两点之间的路线规划信息，获取两个地点的通行方式。origin: 起点坐标(经度，纬度)，"
                "destination: 终点坐标(经度，纬度)，mode: 交通方式(driving/walking/transit)")
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10),
       retry=retry_if_exception_type(httpx.HTTPError))
async def get_route_info(origin: str, destination: str, mode: str = "transit") -> str:
    """高德地图路线规划工具"""
    await rate_limiter.acquire("amap")
    AMAP_KEY = os.getenv("AMAP_API_KEY")

    if not AMAP_KEY:
        return "错误：未配置高德地图 API Key"

    mode_map = {

        "transit": "transit/integrated"
    }
    api_mode = mode_map.get(mode.lower())

    # 全部统一用 V5 接口，公交不需要 city 参数
    url = f"https://restapi.amap.com/v5/direction/{api_mode}"
    if api_mode == "transit/integrated":
        params = {
            "key": AMAP_KEY,
            "origin": origin,
            "destination": destination,
            "city1": "110000",  # 必须是城市编码，不是中文名
            "city2": "110000",  # 必须是城市编码
            "show_fields": "cost"

        }

    try:
        # 🔥 2. 替换为 httpx 异步请求
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "weather_agent_prompt.txt" and data.get("info") == "OK":
            route = data.get("route", {})

            if api_mode == "transit/integrated":
                # V5 公交的字段是 `transits`
                transits = route.get("transits", [])
                if not transits:
                    return "未找到公交方案"
                plan = transits[0]
                distance = int(plan.get("distance", 0)) / 1000
                total_duration_seconds = int(plan["cost"]["duration"])
                total_duration_minutes = total_duration_seconds // 60

                steps = []
                for seg in plan.get("segments", []):
                    bus = seg.get("bus", {})
                    lines = bus.get("buslines", [])
                    for line in lines:
                        # 线路名
                        name = line.get("name", "未知")
                        # 上车站
                        departure = line.get("departure_stop", {}).get("name", "未知")
                        # 下车站
                        arrival = line.get("arrival_stop", {}).get("name", "未知")
                        steps.append(f"{name}【{departure} → {arrival}】")

                return (
                    f"公交方案：约{distance:.1f}公里 | 耗时{total_duration_minutes}分钟\n"
                    f"乘坐路线：{' → '.join(steps)}"
                )
        return f"路线查询失败：{data.get('info', '未知错误')}"
    except Exception as e:
        return f"路线查询出错：{str(e)}"


# @mcp.tool(description="搜索旅行相关的风景图片。当用户需要查看某个景点、城市或地区的实景照片时使用此工具。"
#                       "参数：query-搜索关键词（如'三亚海滩'、'桂林山水'），count-返回图片数量（默认3张，最多10张）。返回包含图片URL、描述和作者信息的列表。")
# @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10),
#        retry=retry_if_exception_type(httpx.HTTPError))
# def search_travel_images(query: str, count: int = 3):
#     """
#     旅行图片搜索工具
#
#     Args:
#         query: 搜索关键词（如：三亚海滩、桂林山水）
#         count: 返回图片数量
#
#     Returns:
#         包含图片信息的字典
#     """
#     if not settings.unsplash_access_key:
#         return {
#             "success": False,
#             "error": "Unsplash API Key 未配置",
#             "images": []
#         }
#
#     url = "https://api.unsplash.com/search/photos"
#     params = {
#         "query": query,
#         "client_id": settings.unsplash_access_key,
#         "count": min(count, 10),  # 限制最大数量
#         "orientation": "landscape"
#     }
#
#     try:
#         log.info(f"[图片搜索] 查询: {query}, 数量: {count}")
#         response = requests.get(url, params=params, timeout=10)
#
#         if response.status_code == 200:
#             data = response.json()
#             results = [{
#                 "url": item.get("urls", {}).get("regular"),
#                 "alt": item.get("alt_description", ""),
#                 "author": item.get("user", {}).get("name"),
#                 "thumbnail": item.get("urls", {}).get("small")
#             } for item in data.get("results", [])]
#
#             log.info(f"[图片搜索] 成功获取 {len(results)} 张图片")
#             return {
#                 "success": True,
#                 "images": results,
#                 "total": len(results)
#             }
#         else:
#             log.error(f"[图片搜索] API 请求失败: {response.status_code}")
#             return {
#                 "success": False,
#                 "error": f"API 请求失败: {response.status_code}",
#                 "images": []
#             }
#     except Exception as e:
#         log.error(f"[图片搜索] 异常: {str(e)}")
#         return {
#             "success": False,
#             "error": str(e),
#             "images": []
#         }
