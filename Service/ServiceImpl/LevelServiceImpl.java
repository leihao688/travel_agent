package org.example.travel_commend.Service.ServiceImpl;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Mapper.UserMapper;
import org.example.travel_commend.Service.LevelService;
import org.example.travel_commend.entity.User;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;

/**
 * 用户等级服务实现类
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LevelServiceImpl implements LevelService {

    private final UserMapper userMapper;

    // 各等级所需经验值
    private static final int[] EXP_THRESHOLDS = {0, 100, 500, 1500, 5000};

    // 等级名称
    private static final String[] LEVEL_NAMES = {"", "新用户", "活跃用户", "优质用户", "资深用户", "核心用户"};

    // 等级颜色（用于前端展示）
    private static final String[] LEVEL_COLORS = {"", "#909399", "#67c23a", "#409eff", "#e6a23c", "#f56c6c"};

    @Override
    public int calculateLevel(int exp) {
        if (exp < EXP_THRESHOLDS[1]) {
            return 1;
        } else if (exp < EXP_THRESHOLDS[2]) {
            return 2;
        } else if (exp < EXP_THRESHOLDS[3]) {
            return 3;
        } else if (exp < EXP_THRESHOLDS[4]) {
            return 4;
        } else {
            return 5;
        }
    }

    @Override
    public int getExpNeededForNextLevel(int level) {
        if (level >= 5) {
            return Integer.MAX_VALUE; // 已满级
        }
        return EXP_THRESHOLDS[level];
    }

    @Override
    public String getLevelName(int level) {
        if (level < 1 || level > 5) {
            return "未知";
        }
        return LEVEL_NAMES[level];
    }

    @Override
    public String getLevelColor(int level) {
        if (level < 1 || level > 5) {
            return "#909399";
        }
        return LEVEL_COLORS[level];
    }

    @Override
    @Transactional
    public boolean addExp(Long userId, int exp, ExpType type) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            return false;
        }

        // 检查是否已满级
        if (user.getLevel() >= 5) {
            return false;
        }

        // 检查今日是否已达到上限
        int todayLimit = type.getDailyLimit();
        int currentTodayExp = user.getTodayExp() != null ? user.getTodayExp() : 0;

        // 计算今日还能获得的经验
        int remainingTodayExp = Math.max(0, todayLimit - currentTodayExp);
        if (remainingTodayExp <= 0) {
            log.info("用户 {} 今日{}经验已达上限", userId, type.name());
            return false;
        }

        // 计算实际获得的经验
        int actualExp = Math.min(exp, remainingTodayExp);

        // 更新用户经验
        int newExp = (user.getExp() != null ? user.getExp() : 0) + actualExp;
        int newTodayExp = currentTodayExp + actualExp;

        // 计算新等级
        int oldLevel = user.getLevel() != null ? user.getLevel() : 1;
        int newLevel = calculateLevel(newExp);

        // 更新用户信息
        user.setExp(newExp);
        user.setTodayExp(newTodayExp);
        user.setLevel(newLevel);

        boolean updated = userMapper.updateById(user) > 0;

        if (updated && newLevel > oldLevel) {
            log.info("用户 {} 升级了！等级: {} → {}", userId, oldLevel, newLevel);
            return true;
        }

        return false;
    }

    @Override
    @Transactional
    public boolean checkDailyLoginReward(Long userId) {
        User user = userMapper.selectById(userId);
        if (user == null) {
            return false;
        }

        LocalDateTime lastLogin = user.getLastLoginDate();
        LocalDateTime now = LocalDateTime.now();

        // 获取今天的开始时间
        LocalDate today = LocalDate.now();
        LocalDateTime todayStart = today.atStartOfDay();

        // 如果上次登录是今天之前
        if (lastLogin == null || lastLogin.isBefore(todayStart)) {
            // 检查是否是连续登录
            boolean isContinuous = false;
            if (lastLogin != null) {
                // 上次登录是昨天
                LocalDate yesterday = today.minusDays(1);
                LocalDateTime yesterdayStart = yesterday.atStartOfDay();
                LocalDateTime yesterdayEnd = yesterday.atTime(LocalTime.MAX);
                isContinuous = !lastLogin.isBefore(yesterdayStart) && !lastLogin.isAfter(yesterdayEnd);
            }

            // 记录登录日期
            user.setLastLoginDate(now);

            // 如果是连续登录，给予奖励
            if (isContinuous) {
                addExp(userId, ExpType.DAILY_LOGIN.getExp(), ExpType.DAILY_LOGIN);
                log.info("用户 {} 连续登录，获得经验奖励", userId);
                return true;
            } else {
                // 首次登录或断签，只记录登录日期
                userMapper.updateById(user);
                return false;
            }
        }

        return false;
    }

    @Override
    public int getLevelProgress(User user) {
        if (user == null || user.getLevel() == null || user.getLevel() >= 5) {
            return 100;
        }

        int level = user.getLevel();
        int exp = user.getExp() != null ? user.getExp() : 0;

        int currentThreshold = level == 1 ? 0 : EXP_THRESHOLDS[level - 1];
        int nextThreshold = EXP_THRESHOLDS[level];

        int expInLevel = exp - currentThreshold;
        int expNeeded = nextThreshold - currentThreshold;

        return (int) ((expInLevel * 100.0) / expNeeded);
    }
}