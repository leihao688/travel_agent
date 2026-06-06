from agent.tools.agent_tools import mcp
if __name__ == '__main__':
    # 启动本地 MCP 服务器
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8081,
        path="/mcp"
    )