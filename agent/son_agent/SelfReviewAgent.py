from agent.tools.middleware import current_agent_name
from utils.prompt_load import logic_review_prompts_load, guard_sys_prompts_load
from models.factor import chat_model
from utils.logger_tool import get_logger
import asyncio

log = get_logger(__name__)


class SelfReviewAgent:
    def __init__(self):
        self.system_prompt = logic_review_prompts_load()

    async def review(self, raw_content: str) -> tuple[bool, str, str]:
        token = current_agent_name.set("SelfReviewAgent")
        try:
            res = await chat_model.ainvoke([
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": raw_content}])
            lines = res.content.strip().split("\n")
            log.info(f"[SelfReviewAgent] 评审结果: {lines}")

            # 🔥 增强解析：防止 LLM 输出多余空格或标点
            first_line = lines[0].strip().replace("：", ":").split(":")[0] if lines else ""
            reason = lines[1].strip() if len(lines) > 1 else "无"
            suggestion = lines[2].strip() if len(lines) > 2 else "无需修正"
            is_valid = first_line == "合格"
            return is_valid, reason, suggestion
        except Exception as e:
            log.warning(f"逻辑评审出错: {e}")
            return True, "", "无需修正"  # 出错默认放行，避免死循环
        finally:
            current_agent_name.reset(token)


class ContentGuardrailAgent:
    def __init__(self):
        self.system_prompt = guard_sys_prompts_load()

    async def guard(self, raw_content: str) -> str:
        token = current_agent_name.set("SelfReviewAgent")
        try:
            res = await chat_model.ainvoke([
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": "请检查以下内容，并给出建议：\n" + raw_content}
            ])
            return res.content.strip()
        except Exception as e:
            log.warning(f"内容护栏修正失败: {e}")
            return raw_content
        finally:
            current_agent_name.reset(token)


if __name__ == "__main__":
    async def test_self_review():
        """测试逻辑评审 Agent"""
        print("\n" + "=" * 60)
        print("🧪 测试 weather_agent_prompt.txt: SelfReviewAgent - 逻辑评审")
        print("=" * 60)

        agent = SelfReviewAgent()
        agent1 = ContentGuardrailAgent()

        # 测试用例 weather_agent_prompt.txt: 合格的行程
        valid_content = """
        第一天：上午游览天涯海角（门票81元），下午前往南山文化旅游区（门票128元）
        第二天：上午参观亚龙湾热带天堂森林公园（门票158元），下午在海边休息
        """

        print(f"\n📝 评审内容:\n{valid_content}")
        is_valid, reason, suggestion = await agent.review(valid_content)
        print(f"\n✅ 评审结果:")
        print(f"  - 是否合格: {is_valid}")
        print(f"  - 原因: {reason}")
        print(f"  - 建议: {suggestion}")
        res = await agent1.guard(valid_content)
        print(res)

        # 测试用例 2: 不合格的行程
        invalid_content = """
        第一天：早上从北京飞到三亚，中午在巴黎吃午餐，晚上回纽约看自由女神像
        """

        print(f"\n📝 评审内容:\n{invalid_content}")
        is_valid, reason, suggestion = await agent.review(invalid_content)
        print(f"\n✅ 评审结果:")
        print(f"  - 是否合格: {is_valid}")
        print(f"  - 原因: {reason}")
        print(f"  - 建议: {suggestion}")


    asyncio.run(test_self_review())
