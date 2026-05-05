from agent.tools.agent_tools import mcp
if __name__ == '__main__':
    # 🔥 最简单、兼容所有版本的写法
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8080,
        path="/mcp"
    )