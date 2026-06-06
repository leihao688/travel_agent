from utils.config_load import prompts_config
from utils.logger_tool import get_logger
from utils.path_handle import get_absolute_path_with_base, get_project_root
from datetime import datetime

logger = get_logger(__name__)


def load_prompt(config_key: str) -> str:
    """
    通用提示词加载函数

    Args:
        config_key: yaml配置中的提示词路径键名

    Returns:
        提示词内容字符串
    """
    if config_key not in prompts_config:
        error_msg = f"在yaml没有配置['{config_key}']"
        logger.error(error_msg)
        raise KeyError(error_msg)

    try:
        prompt_path = get_absolute_path_with_base(
            get_project_root(),
            prompts_config[config_key]
        )
    except Exception as e:
        logger.error(f"获取['{config_key}']路径出错: {str(e)}")
        raise e

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取['{config_key}']提示词文件出错: {str(e)}")
        raise e


def system_prompts_load():
    return load_prompt('rag_summarize_path')


def attraction_prompts_load():
    return load_prompt('rag_attraction_path')


def hotel_prompts_load():
    return load_prompt('rag_hotel_path')


def route_prompts_load():
    return load_prompt('rag_route_path')


def weather_prompts_load():
    prompt = load_prompt('rag_weather_path')
    today = datetime.now().strftime("%Y-%m-%d")
    return f"【当前日期】{today}（请以此为基准计算“明天/后天”等日期）\n\n{prompt}"


def rag_prompts_load():
    return load_prompt('rag_summarize_path')


def main_prompts_load():
    return load_prompt('rag_main_path')


def intend_prompts_load():
    return load_prompt('intend_path')


def formatter_prompts_load():
    return load_prompt('formatter_path')


def logic_review_prompts_load():
    return load_prompt('logic_review_path')


def guard_sys_prompts_load():
    return load_prompt('guard_sys_path')


def rag_rewrite_prompts_load():
    return load_prompt('rag_rewrite_path')
