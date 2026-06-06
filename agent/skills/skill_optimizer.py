"""
Skill 性能监控和优化器
"""
import json
import time
from typing import Dict, List
from agent.skills.skill_registry import skill_registry
from utils.logger_tool import get_logger

log = get_logger(__name__)


class SkillOptimizer:
    """Skill 性能监控和优化器"""

    def __init__(self):
        self.performance_log = []

    def log_performance(self, skill_name: str, query: str,
                        execution_time: float, success: bool,
                        user_feedback: str = None):
        """记录技能执行性能"""
        record = {
            "timestamp": time.time(),
            "skill_name": skill_name,
            "query": query[:100],  # 只保存前100字符
            "execution_time": execution_time,
            "success": success,
            "user_feedback": user_feedback
        }
        self.performance_log.append(record)

        # 更新技能统计
        skill = skill_registry.get_skill(skill_name)
        if skill:
            skill.record_usage(success)

        log.info(f"[SkillOptimizer] {skill_name}: "
                 f"耗时={execution_time:.2f}s, "
                 f"成功={success}")

    def get_performance_report(self) -> Dict:
        """生成性能报告"""
        stats = skill_registry.get_skill_stats()

        report = {
            "skill_statistics": stats,
            "recent_performances": self.performance_log[-20:],  # 最近20条记录
            "recommendations": self._generate_recommendations(stats)
        }

        return report

    @staticmethod
    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """基于统计数据生成优化建议"""
        recommendations = []

        for skill_name, skill_stats in stats.items():
            # 低成功率警告
            if skill_stats["success_rate"] < 0.7 and skill_stats["match_count"] > 10:
                recommendations.append(
                    f"⚠️ 技能 '{skill_name}' 成功率较低 ({skill_stats['success_rate']:.1%})，"
                    f"建议检查提示词或工具配置"
                )

            # 高频使用但未优化
            if skill_stats["match_count"] > 50 and skill_stats["success_rate"] < 0.9:
                recommendations.append(
                    f"💡 技能 '{skill_name}' 使用频繁但仍有优化空间，"
                    f"考虑增加更多示例或调整优先级"
                )

        return recommendations

    def export_stats(self, filepath: str = "logs/skill_stats.json"):
        """导出统计数据到文件"""
        report = self.get_performance_report()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log.info(f"[SkillOptimizer] 统计数据已导出到 {filepath}")


# 全局单例
skill_optimizer = SkillOptimizer()
