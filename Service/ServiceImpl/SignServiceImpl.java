package org.example.travel_commend.Service.ServiceImpl;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Service.LevelService;
import org.example.travel_commend.Service.SignService;
import org.example.travel_commend.VO.SignStatusVO;
import org.example.travel_commend.dto.Result;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.LocalDate;

import static org.example.travel_commend.Util.RedisConstants.SIGN_KEY_PREFIX;

@Slf4j
@Service
@RequiredArgsConstructor
public class SignServiceImpl implements SignService {
    private final StringRedisTemplate stringRedisTemplate;
    private final LevelService levelService;

    private String getSignKey(Long userId, int year, int month) {
        return SIGN_KEY_PREFIX + userId + ":" + year + ":" + month;
    }

    private int getDayOfMonthOffset(LocalDate date) {
        return date.getDayOfMonth() - 1;
    }

    @Override
    public Result<Void> sign(Long userId) {
        LocalDate today = LocalDate.now();
        int year = today.getYear();
        int month = today.getMonthValue();
        int offset = getDayOfMonthOffset(today);
        String key = getSignKey(userId, year, month);

        Boolean result = stringRedisTemplate.opsForValue().setBit(key, offset, true);

        if (result != null && !result) {
            log.info("用户 {} 签到成功", userId);
            levelService.addExp(userId, 2, LevelService.ExpType.DAILY_LOGIN);
            return Result.success();
        }

        return Result.error("今天已签到");
    }

    @Override
    public boolean isSignedToday(Long userId) {
        LocalDate today = LocalDate.now();
        String key = getSignKey(userId, today.getYear(), today.getMonthValue());
        return Boolean.TRUE.equals(stringRedisTemplate.opsForValue().getBit(key, getDayOfMonthOffset(today)));
    }

    @Override
    public int getMonthSignCount(Long userId) {
        LocalDate today = LocalDate.now();
        return getMonthSignCount(userId, today.getYear(), today.getMonthValue());
    }

    private int getMonthSignCount(Long userId, int year, int month) {
        String key = getSignKey(userId, year, month);
        String value = stringRedisTemplate.opsForValue().get(key);

        if (value == null) {
            return 0;
        }

        int count = 0;
        for (char c : value.toCharArray()) {
            count += Integer.bitCount(c);
        }
        return count;
    }

    @Override
    public int getContinuousSignDays(Long userId) {
        LocalDate today = LocalDate.now();
        String key = getSignKey(userId, today.getYear(), today.getMonthValue());

        int continuousDays = 0;
        int todayOffset = getDayOfMonthOffset(today);

        for (int i = 0; i <= todayOffset; i++) {
            int offset = todayOffset - i;
            Boolean isSigned = stringRedisTemplate.opsForValue().getBit(key, offset);

            if (Boolean.TRUE.equals(isSigned)) {
                continuousDays++;
            } else {
                break;
            }
        }

        return continuousDays;
    }

    @Override
    public String getSignBitmap(Long userId) {
        LocalDate today = LocalDate.now();
        return stringRedisTemplate.opsForValue().get(getSignKey(userId, today.getYear(), today.getMonthValue()));
    }

    @Override
    public boolean[] getMonthSignDays(Long userId, int year, int month) {
        LocalDate firstDay = LocalDate.of(year, month, 1);
        LocalDate lastDay = firstDay.plusMonths(1).minusDays(1);
        int daysInMonth = lastDay.getDayOfMonth();

        String key = getSignKey(userId, year, month);
        boolean[] result = new boolean[daysInMonth];

        for (int i = 0; i < daysInMonth; i++) {
            result[i] = Boolean.TRUE.equals(stringRedisTemplate.opsForValue().getBit(key, i));
        }

        return result;
    }

    @Override
    public Result<SignStatusVO> getSignStatus(Long userId) {
        SignStatusVO vo = new SignStatusVO();
        vo.setSignedToday(isSignedToday(userId));
        vo.setContinuousDays(getContinuousSignDays(userId));
        vo.setMonthCount(getMonthSignCount(userId));
        return Result.success(vo);
    }
}
