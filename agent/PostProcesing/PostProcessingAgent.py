from utils.prompt_load import logic_review_prompts_load
from utils.logger_tool import get_logger
from models.factor import chat_model
log = get_logger(__name__)


class PostProcessingAgent:
    def __init__(self, max_retry: int = 2):
        self.max_retry = max_retry

    async def logic_review(self, user_query: str, raw_output: str) -> tuple[bool, str]:
        """检查逻辑问题（融合了原 logic_review_prompt 的核心标准）"""
        review_prompt = f"""
    你是旅行安全与逻辑专家。请基于【用户原始需求】对【行程方案】进行深度逻辑压力测试。

    【用户原始需求】：{user_query}
    【待评审方案】：
    {raw_output}

    ### 审查核心（必须严格检查）：
    1. 【天数对齐】：方案覆盖的天数是否严格等于用户需求？（如用户说玩2天，必须有Day1和Day2）
    2. 【地点对齐】：是否围绕用户指定的城市展开？
    3. 【可行性】：时间线、交通动线是否在物理世界中行得通？

    ### 输出格式（严格两行）：
    第一行：合格 / 不合格
    第二行：若不合格，简述核心冲突（例如：用户要求2天，方案只有1天）；若合格，填无
    """
        try:
            res = await chat_model.ainvoke(review_prompt)
            lines = res.content.strip().split("\n")
            is_valid = "合格" in lines[0]
            reason = lines[1].strip() if len(lines) > 1 else "无"
            return is_valid, reason
        except Exception as e:
            return True, "无"

    async def auto_fix(self, user_query: str, raw_output: str, reason: str) -> str:
        """自动根据逻辑问题生成修正版"""
        fix_prompt = f"""
    之前的方案存在问题：{reason}
    【用户原始需求】：{user_query}
    【原方案】：{raw_output}

    任务：请基于用户需求和原方案进行修正。
    要求：
    1. 解决上述指出的逻辑问题。
    2. 保持原方案的结构和风格。
    3. 直接输出修正后的完整方案，不要解释。
    """
        try:
            res = await chat_model.ainvoke(fix_prompt)
            return res.content.strip()
        except Exception as e:
            log.warning(f"自动修正异常: {e}")
            return raw_output

    async def format_output(self, output: str) -> str:
        """简单格式化输出，去除多余空格和空行"""
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return "\n".join(lines)

