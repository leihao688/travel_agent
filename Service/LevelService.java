package org.example.travel_commend.Service;

import org.example.travel_commend.entity.User;

/**
 * 用户等级服务接口
 */
public interface LevelService {

    /**
     * 根据经验值计算等级
     *
     * @param exp 经验值
     * @return 等级（1-5）
     */
    int calculateLevel(int exp);

    /**
     * 获取升级所需经验值
     *
     * @param level 当前等级
     * @return 升级所需经验值
     */
    int getExpNeededForNextLevel(int level);

    /**
     * 获取等级名称
     *
     * @param level 等级
     * @return 等级名称
     */
    String getLevelName(int level);

    /**
     * 获取等级颜色（用于展示）
     *
     * @param level 等级
     * @return 颜色代码
     */
    String getLevelColor(int level);

    /**
     * 添加经验值
     *
     * @param userId 用户ID
     * @param exp    经验值
     * @param type   获取经验的类型
     * @return 是否升级
     */
    boolean addExp(Long userId, int exp, ExpType type);

    /**
     * 检查并处理连续登录奖励
     *
     * @param userId 用户ID
     * @return 是否获得连续登录奖励
     */
    boolean checkDailyLoginReward(Long userId);

    /**
     * 获取等级进度百分比
     *
     * @param user 用户
     * @return 进度百分比（0-100）
     */
    int getLevelProgress(User user);

    /**
     * 经验获取类型枚举
     */
    enum ExpType {
        /**
         * 发布评论
         */
        COMMENT(10, 50),
        /**
         * 评论被点赞
         */
        COMMENT_LIKED(5, 20),
        /**
         * 发布回复
         */
        REPLY(5, 30),
        /**
         * 连续登录
         */
        DAILY_LOGIN(2, 2);

        private final int exp;
        private final int dailyLimit;

        ExpType(int exp, int dailyLimit) {
            this.exp = exp;
            this.dailyLimit = dailyLimit;
        }

        public int getExp() {
            return exp;
        }

        public int getDailyLimit() {
            return dailyLimit;
        }
    }
}