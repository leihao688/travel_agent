from models.factor import embedding_model, chat_model
from langchain_chroma import Chroma
import json
from utils.config_load import chorma_config
from utils.logger_tool import get_logger
from utils.path_handle import get_absolute_path_with_base, get_project_root

log = get_logger(__name__)


class LongTermMemory:
    def __init__(self):
        self.embedding_model = embedding_model
        self.vector_store = Chroma(
            collection_name=chorma_config["memory_collection_name"],
            embedding_function=self.embedding_model,
            persist_directory=get_absolute_path_with_base(get_project_root(), chorma_config["persist_directory"])
        )
        self.chat_model = chat_model

    async def extract_summary(self, messages: list) -> str:
        # 先将消息转换为文本格式
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages[-10:]
        ])

        prompt = f"""你是一个旅行助手的信息提取专家。请从对话中提取用户的**长期偏好和重要事实**。

        ## ⚠️ 严格提取规则（非常重要）：

        ### ✅ 应该提取的内容（长期有效）：
        1. **明确的旅行偏好**：用户明确表达的喜好
           - 例如："我喜欢海滩"、"我偏好历史文化"、"我讨厌爬山"

        2. **用户身份特征**：稳定的个人信息
           - 例如："我是学生"、"我是商务人士"、"我带孩子出行"

        3. **预算习惯**：一贯的消费倾向
           - 例如："我通常选择经济型酒店"、"我预算比较充裕"

        4. **明确禁忌**：不会轻易改变的限制
           - 例如："我对海鲜过敏"、"我不能吃辣"、"我恐高"

        ### ❌ 绝对不要提取的内容：
        1. **问候语和闲聊**：如"你好"、"谢谢"、"再见"
        2. **一次性行程计划**：如"我明天要去海南"、"这周末去北京"
        3. **临时查询**：如"故宫门票多少钱"、"今天天气如何"
        4. **假设性问题**：如"如果我去三亚会怎样"
        5. **工具调用结果**：如天气信息、景点列表、酒店推荐等
        6. **AI的回复内容**：只关注用户说的话
        7. **不确定的表达**：如"可能"、"也许"、"考虑"

        ### 🔍 判断标准：
        问自己：这个信息在**一个月后**还有效吗？
        - 如果无效 → 不要提取
        - 如果有效 → 可以提取

        ## 输出格式：
        只输出 JSON 格式，不要任何解释。格式如下：
        {{"preferences": ["偏好1", "偏好2"], "facts": ["事实1", "事实2"]}}

        如果没有任何值得记录的长期信息，**必须**输出：{{"preferences": [], "facts": []}}

        ## 对话内容：
        {conversation_text}
        """
        try:
            res = await self.chat_model.ainvoke(prompt)
            content = res.content.strip()
            return content
        except Exception as e:
            print(f"LLM 提取用户信息摘要失败：{str(e)}")
            return json.dumps({"preferences": [], "facts": []}, ensure_ascii=False)

    async def store_summary(self, user_id: str, messages: list):
        """将用户画像/偏好摘要存储到向量库中"""
        if len(messages) < 6:  # 对话太短不存储
            return
            # 提取摘要
        summary_json = await self.extract_summary(messages)
        summary_data = json.loads(summary_json)

        # 如果没有提取到有效信息，不存储
        if not summary_data.get("preferences") and not summary_data.get("facts"):
            log.info(f"[LongTermMemory] 未提取到有效长期记忆，跳过存储")
            return

        # 检查是否已经存在相似的记录（去重）
        existing_memories = self.retrieve(user_id)
        if existing_memories:
            # 简单去重：如果新提取的内容已经存在于历史记忆中，跳过
            new_prefs = set(summary_data['preferences'])
            new_facts = set(summary_data['facts'])

            # 检查是否大部分内容已经存在
            if all(pref in existing_memories for pref in new_prefs) and \
                    all(fact in existing_memories for fact in new_facts):
                log.info(f"[LongTermMemory] 记忆已存在，跳过重复存储")
                return

        summary_text = f"用户偏好: {', '.join(summary_data['preferences'])} | 用户事实: {', '.join(summary_data['facts'])}"

        # 存入向量库
        self.vector_store.add_texts(
            texts=[summary_text],
            metadatas=[{
                "user_id": user_id,
                "timestamp": __import__('time').time(),
                "preferences": json.dumps(summary_data['preferences'], ensure_ascii=False),
                "facts": json.dumps(summary_data['facts'], ensure_ascii=False)
            }]
        )
        log.info(f"✅ 长期记忆已保存：{user_id} | {summary_text}")

    def retrieve(self, user_id: str) -> str:
        """
                检索用户的长期记忆（用户画像）

                Args:
                    user_id: 用户ID（Java端传入的真实用户标识）

                Returns:
                    用户的历史偏好记忆文本（用户画像）
                """
        try:
            if not user_id or user_id == "default":
                log.info("[LongTermMemory] user_id 为空或使用默认值，无长期记忆")
                return ""

            # 直接获取该用户的所有长期记忆（用户画像）
            results = self.vector_store.get(
                where={"user_id": user_id},
                limit=chorma_config.get("memory_k", 5)
            )

            documents = results.get('documents', [])

            if not documents:
                log.info(f"[LongTermMemory] 用户 {user_id} 暂无长期记忆")
                return ""

            # 格式化输出为用户画像
            formatted_memories = []
            for i, memory in enumerate(documents, 1):
                formatted_memories.append(memory)

            user_profile = "\n".join(formatted_memories)
            log.info(f"[LongTermMemory] 检索到用户 {user_id} 的画像信息: {user_profile[:100]}...")
            return user_profile

        except Exception as e:
            log.error(f"⚠️ 长期记忆检索失败：{e}", exc_info=True)
            return ""
