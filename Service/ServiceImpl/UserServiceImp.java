package org.example.travel_commend.Service.ServiceImpl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.RandomUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Mapper.UserMapper;
import org.example.travel_commend.Service.LevelService;
import org.example.travel_commend.Service.UserService;
import org.example.travel_commend.Util.*;
import org.example.travel_commend.VO.UserVO;
import org.example.travel_commend.dto.*;
import org.example.travel_commend.entity.User;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.concurrent.TimeUnit;

import static org.example.travel_commend.Util.CommonContants.USER_PREFIX;
import static org.example.travel_commend.Util.RedisConstants.LOGIN_USER_KEY;
import static org.example.travel_commend.Util.RedisConstants.LOGIN_USER_TTL;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserServiceImp extends ServiceImpl<UserMapper, User> implements UserService {
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();
    private final JwtUtil jwtUtil;
    private final CodeUtil codeUtil;
    private final StringRedisTemplate stringRedisTemplate;
    private final LevelService levelService;

    @Override
    @Transactional
    public Result<Void> register(UserRegisterDTO userRegisterDTO) {
        String phone = userRegisterDTO.getPhone();
        String code = userRegisterDTO.getCode();

        if (!RegexUtils.isMobile(phone)) {
            return Result.error("手机号格式不正确");
        }

        if (!codeUtil.verifyCode(phone, code)) {
            return Result.error("验证码错误或已过期");
        }

        User existingUser = query().eq("phone", phone).one();

        if (existingUser != null) {
            return Result.error("该手机号已注册");
        }

        User user = new User();
        user.setPhone(phone);
        user.setUsername(USER_PREFIX + phone);
        user.setNickname(USER_PREFIX + RandomUtil.randomNumbers(6));
        user.setPassword(passwordEncoder.encode(userRegisterDTO.getPassword()));

        save(user);

        log.info("用户注册成功 - 手机号: {}", phone);
        return Result.success();
    }

    @Override
    public Result<String> sendCode(String phone) {
        if (!RegexUtils.isMobile(phone)) {
            return Result.error("手机号格式不正确");
        }

        if (codeUtil.isCodeExists(phone)) {
            Long expireTime = codeUtil.getCodeExpireTime(phone);
            return Result.error("验证码已发送，请" + expireTime + "秒后再试");
        }

        codeUtil.sendCode(phone);
        return Result.success("验证码发送成功");
    }

    @Override
    public Result<String> loginByCode(String phone, String code) {
        if (!RegexUtils.isMobile(phone)) {
            return Result.error("手机号格式不正确");
        }

        User user = query().eq("phone", phone).one();
        if (user == null) {
            return Result.error("用户不存在，请先注册");
        }

        if (!codeUtil.verifyCode(phone, code)) {
            return Result.error("验证码错误或已过期");
        }
        String token = jwtUtil.generateToken(user.getId(), user.getPhone());
        stringRedisTemplate.opsForValue().set(LOGIN_USER_KEY + phone, token, LOGIN_USER_TTL, TimeUnit.HOURS);

        // 检查连续登录奖励
        levelService.checkDailyLoginReward(user.getId());

        log.info("验证码登录成功 - 手机号: {}", phone);
        return Result.success(token);

    }

    @Override
    public Result<String> loginByPassword(String phone, String password) {
        if (!RegexUtils.isMobile(phone)) {
            return Result.error("手机号格式不正确");
        }

        User user = query().eq("phone", phone).one();
        if (user == null) {
            return Result.error("用户不存在");
        }

        if (!passwordEncoder.matches(password, user.getPassword())) {
            return Result.error("密码错误");
        }

        String token = jwtUtil.generateToken(user.getId(), user.getPhone());
        stringRedisTemplate.opsForValue().set(LOGIN_USER_KEY + phone, token, LOGIN_USER_TTL, TimeUnit.HOURS);
        
        // 检查连续登录奖励
        levelService.checkDailyLoginReward(user.getId());
        
        log.info("密码登录成功 - 手机号: {}", phone);
        return Result.success(token);
    }

    @Override
    public Result<UserVO> getUserInfo() {
        Long userId = UserHolder.getUserId();
        if (userId == null) {
            return Result.error("用户未登录");
        }
        User user = query().eq("id", userId).one();
        // 将 User 转换为 UserVO
        UserVO userVO = BeanUtil.copyProperties(user, UserVO.class);

        // 填充等级相关信息
        int level = user.getLevel() != null ? user.getLevel() : 1;
        userVO.setLevelName(levelService.getLevelName(level));
        userVO.setLevelColor(levelService.getLevelColor(level));
        userVO.setExp(user.getExp() != null ? user.getExp() : 0);
        userVO.setExpNeeded(levelService.getExpNeededForNextLevel(level));
        userVO.setLevelProgress(levelService.getLevelProgress(user));

        return Result.success(userVO);
    }

    @Override
    public Result<Void> logout() {
        Long userId = UserHolder.getUserId();
        if (userId == null) {
            return Result.error("用户未登录");
        }
        UserDTO userDTO = UserHolder.getUser();
        String redisKey = LOGIN_USER_KEY + userDTO.getPhone();
        stringRedisTemplate.delete(redisKey);
        log.info("用户退出登录 - 用户ID: {}", userId);
        return Result.success();
    }

    @Override
    public Result<Void> updateUserInfo(UserUpdateDTO userUpdateDTO) {
        Long userId = UserHolder.getUserId();
        if (userId == null) {
            return Result.error("用户未登录");
        }
        User existingUser = query().eq("id", userId).one();
        if (existingUser == null) {
            return Result.error("用户不存在");
        }
        BeanUtil.copyProperties(userUpdateDTO, existingUser);
        boolean updated = updateById(existingUser);
        if (!updated) {
            return Result.error("更新用户信息失败");
        }
        return Result.success();

    }

}
