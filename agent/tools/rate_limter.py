"""
全局令牌桶限流器 - 保护外部 API 不被限流
"""
import asyncio
from aiolimiter import AsyncLimiter
from utils.logger_tool import get_logger

log = get_logger(__name__)


class RateLimiter:
    """全局限流器（单例）"""
    _instance = None
    _limiters = {}
    # 🔥 核心优化：预设各 API 的限流策略 (max_rate, time_period)
    API_LIMITS = {
        "qweather": (5, 1.0),  # 和风天气：5 次/秒
        "amap": (5, 1.0),  # 高德地图：5 次/秒
        "baidu": (2, 1.0)  # 百度千帆：2 次/秒 (通常较慢)
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_limiter(self, api_name: str):
        if api_name not in self._limiters:
            max_rate, time_period = self.API_LIMITS.get(api_name, (10, 1.0))
            self._limiters[api_name] = AsyncLimiter(max_rate, time_period)
            log.info(f"[RateLimiter] 创建限流器: {api_name} ({max_rate}次/{time_period}秒)")
        return self._limiters[api_name]

    async def acquire(self, api_name: str):
        """等待获取令牌"""
        limiter = self.get_limiter(api_name)
        await limiter.acquire()


# 全局单例
rate_limiter = RateLimiter()
