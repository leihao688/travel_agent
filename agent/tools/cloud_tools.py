"""使用 MCP 官方 SDK 测试高德服务"""
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import os
from dotenv import load_dotenv

load_dotenv()

MCP_URL = os.getenv("MCP_SERVER_URL")
print(f"🔗 正在连接: {MCP_URL}\n")


async def main():
    # 使用 streamable_http_client 连接
    async with streamable_http_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            # weather_agent_prompt.txt. 初始化
            print("🤝 正在初始化...")
            await session.initialize()
            print("✅ 初始化成功\n")

            # 2. 列出工具
            print("📋 获取工具列表:")
            print("=" * 60)
            tools = await session.list_tools()
            print(f"✅ 共 {len(tools.tools)} 个工具")
            for t in tools.tools[:3]:  # 只显示前 3 个
                print(f"   - {t.name}")
            if len(tools.tools) > 3:
                print(f"   ... 还有 {len(tools.tools) - 3} 个工具")

            print("\n" + "=" * 60)
            print("🌤️  测试天气查询 (福州):")
            print("=" * 60)

            # 3. 调用天气工具
            try:
                result = await session.call_tool("maps_weather", {"city": "福州"})
                print(result.content[0].text[:500])  # 只显示前 500 字符
            except Exception as e:
                print(f"❌ 调用失败: {e}")

            print("\n" + "=" * 60)
            print("⏸️  等待 3 秒（避免触发限流）...")
            print("=" * 60)
            await asyncio.sleep(3)

            print("\n🏨 测试地点搜索 (三坊七巷):")
            print("=" * 60)

            # 4. 调用 POI 搜索（增加超时处理）
            try:
                result = await asyncio.wait_for(
                    session.call_tool("maps_text_search", {
                        "keywords": "三坊七巷",
                        "city": "福州",
                        "types": "110000"
                    }),
                    timeout=10
                )
                print(result.content[0].text[:500])
            except asyncio.TimeoutError:
                print("⚠️  请求超时（云端可能限流）")
            except Exception as e:
                print(f"❌ 调用失败: {str(e)[:200]}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ 测试完成（手动中断）")
