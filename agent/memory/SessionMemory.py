import yaml
import redis

from utils.config_load import redis_config


class SessionMemory:
    def __init__(self):
        try:
            redis_conf = redis_config.get("redis",{})
            self.redis = redis.Redis(
                host=redis_conf["host"],
                port=redis_conf["port"],
                db=redis_conf["db"],
                password=redis_conf["password"],
                decode_responses=redis_conf["decode_responses"],
            )
            self.redis.ping()
            print("Redis 连接成功")
        except Exception as e:
            print(f"Redis 配置加载失败，请检查 redis.yaml: {e}")
            raise

    def get_history(self, session_id):
        """
        获取会话历史
        :param session_id: 会话ID
        :return: 会话历史列表
        """
        import json
        key = f"session:{session_id}:history"
        raw_data = self.redis.lrange(key, 0, -1)
        return [json.loads(item) for item in reversed(raw_data)]

    def add_message(self, session_id: str, role: str, content: str, ttl: int = 7200):
        """追加消息并设置过期时间"""
        import json
        key = f"session:{session_id}:history"
        pipe = self.redis.pipeline()
        pipe.lpush(key, json.dumps({"role": role, "content": content}, ensure_ascii=False))
        pipe.ltrim(key, 0, 19)  # 仅保留最近 20 条
        pipe.expire(key, ttl)
        pipe.execute()


if __name__ == '__main__':
    try:
        s = SessionMemory()
        print(f"✅ Redis 对象: {s.redis}")
        s.add_message("test_001", "user", "你好，帮我规划个行程")
        print(f"📝 存入成功: {s.get_history('test_001')}")
    except Exception as e:
        print(f"❌ 运行失败: {e}")
