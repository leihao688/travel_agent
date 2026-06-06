package org.example.travel_commend.Util;

import cn.hutool.core.util.RandomUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

import static org.example.travel_commend.Util.RedisConstants.CODE_EXPIRE_MINUTES;
import static org.example.travel_commend.Util.RedisConstants.CODE_KEY_PREFIX;

@Slf4j
@Component
public class CodeUtil {

    private final StringRedisTemplate stringRedisTemplate;

    public CodeUtil(StringRedisTemplate stringRedisTemplate) {
        this.stringRedisTemplate = stringRedisTemplate;
    }

    public String sendCode(String phone) {
        if (!RegexUtils.isMobile(phone)) {
            throw new IllegalArgumentException("手机号格式不正确");
        }

        String code = RandomUtil.randomNumbers(6);

        String key = CODE_KEY_PREFIX + phone;
        stringRedisTemplate.opsForValue().set(key, code, CODE_EXPIRE_MINUTES, TimeUnit.MINUTES);

        log.info("验证码已发送 - 手机号: {}, 验证码: {}", phone, code);

        return code;
    }

    public boolean verifyCode(String phone, String code) {
        if (!RegexUtils.isMobile(phone)) {
            log.warn("手机号格式不正确: {}", phone);
            return false;
        }

        if (code == null || code.length() != 6) {
            log.warn("验证码格式不正确: {}", code);
            return false;
        }

        String key = CODE_KEY_PREFIX + phone;
        String savedCode = stringRedisTemplate.opsForValue().get(key);

        if (savedCode == null) {
            log.warn("验证码不存在或已过期 - 手机号: {}", phone);
            return false;
        }

        if (!savedCode.equals(code)) {
            log.warn("验证码错误 - 手机号: {}", phone);
            return false;
        }

        stringRedisTemplate.delete(key);
        log.info("验证码验证成功 - 手机号: {}", phone);
        return true;
    }

    public boolean isCodeExists(String phone) {
        if (!RegexUtils.isMobile(phone)) {
            return false;
        }

        String key = CODE_KEY_PREFIX + phone;
        Boolean exists = stringRedisTemplate.hasKey(key);
        return Boolean.TRUE.equals(exists);
    }

    public void clearCode(String phone) {
        if (!RegexUtils.isMobile(phone)) {
            return;
        }

        String key = CODE_KEY_PREFIX + phone;
        stringRedisTemplate.delete(key);
        log.info("验证码已清除 - 手机号: {}", phone);
    }

    public Long getCodeExpireTime(String phone) {
        if (!RegexUtils.isMobile(phone)) {
            return null;
        }

        String key = CODE_KEY_PREFIX + phone;
        return stringRedisTemplate.getExpire(key, TimeUnit.SECONDS);
    }
}
