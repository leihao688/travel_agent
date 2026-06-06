import contextvars
from typing import Callable

from langchain.agents.middleware import wrap_tool_call, before_model, dynamic_prompt, ModelRequest
from langchain_core.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langgraph.types import Command
from utils.logger_tool import get_logger
from langchain.agents import AgentState

from utils.prompt_load import system_prompts_load

logger = get_logger(__name__)
from langgraph.runtime import Runtime

# 这是实现将模型调用信息记录到日志中（比如WeatherQueryAgent）
current_agent_name = contextvars.ContextVar("current_agent_name", default="unknown")


@wrap_tool_call
async def monitor_tool_call(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    # 直接从上下文变量获取 Agent 名称
    agent_name = current_agent_name.get()

    tool_name = request.tool_call["name"]
    tool_args = request.tool_call["args"]
    logger.info(f"[{agent_name}] 调用工具: {tool_name}, 参数: {tool_args}")
    try:

        # 🔥 核心修改：使用 await 调用处理器
        result = await handler(request)
        
        # 详细调试信息
        logger.info(f"[{agent_name}] 工具返回类型: {type(result).__name__}")
        logger.info(f"[{agent_name}] 工具返回结果: {result}")
        
        # 检查并提取工具返回内容中的 JSON 字符串
        if hasattr(result, 'content'):
            logger.info(f"[{agent_name}] result.content 类型: {type(result.content)}")
            logger.info(f"[{agent_name}] result.content 值: {result.content}")
            # 尝试提取 TextContent 中的文本内容
            content = result.content
            if isinstance(content, list) and len(content) > 0:
                logger.info(f"[{agent_name}] content[0] 类型: {type(content[0])}")
                if hasattr(content[0], 'text'):
                    text_content = content[0].text
                    logger.info(f"[{agent_name}] 提取的文本内容: {text_content}")
                    # 检查是否是有效的 JSON
                    if text_content and (text_content.startswith('[') or text_content.startswith('{')):
                        logger.info(f"[{agent_name}] 工具 {tool_name} 执行成功，返回 JSON: {text_content[:100]}...")
                    else:
                        logger.info(f"[{agent_name}] 工具 {tool_name} 执行成功，返回: {text_content[:100]}...")
        
        logger.info(f"[{agent_name}] 工具 {tool_name} 执行成功")
        return result
    except Exception as e:
        logger.error(f"[{agent_name}] 工具 {tool_name} 调用失败: {str(e)}")
        raise e


@before_model
def log_before_model(
        state: AgentState,
        runtime: Runtime
):
    # 同样从上下文变量获取
    #agent_name = current_agent_name.get()

    # logger.info(f"[{agent_name}] 即将调用模型, 带有{len(state['messages'])}条信息")
    # if state['messages']:
    # logger.debug(f"[{agent_name}] 最后一条消息: {type(state['messages'][-weather_agent_prompt.txt]).__name__} | {state['messages'][-weather_agent_prompt.txt].content.strip()}")
    return None
