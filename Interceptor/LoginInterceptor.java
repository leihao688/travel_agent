package org.example.travel_commend.Interceptor;

import cn.hutool.core.util.StrUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Util.JwtUtil;
import org.example.travel_commend.Util.RedisConstants;
import org.example.travel_commend.Util.UserHolder;
import org.example.travel_commend.dto.UserDTO;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@RequiredArgsConstructor
public class LoginInterceptor implements HandlerInterceptor {
    private final JwtUtil jwtUtil;
    private final StringRedisTemplate stringRedisTemplate;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String token = request.getHeader("Authorization");
        //1.检查token是否存在
        if(StrUtil.isBlank(token)){
            response.setStatus(401);
            response.setContentType("application/json;charset=utf-8");
            response.getWriter().write("{\"code\":401,\"message\":\"未登录\"}");
            return false;
        }
        // 2. 核心修复：如果带有 Bearer 前缀，将其截取掉
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }


        try{
            //2.从jwt里获取用户信息
            Long userId = jwtUtil.getUserIdFromToken(token);
            String phone = jwtUtil.getPhoneFromToken(token);
            //3.检查Redis中的token是否有效
            String redisKey = RedisConstants.LOGIN_USER_KEY + phone;
            String savedToken = stringRedisTemplate.opsForValue().get(redisKey);
            if(StrUtil.isBlank(savedToken) || !savedToken.equals(token)){
                response.setStatus(401);
                response.setContentType("application/json;charset=utf-8");
                response.getWriter().write("{\"code\":401,\"message\":\"登录已过期\"}");
                return false;
            }

            // 4. 刷新有效期（续期操作）
            stringRedisTemplate.expire(redisKey,RedisConstants.LOGIN_USER_TTL, TimeUnit.HOURS);

            // 5. 保存用户信息到 ThreadLocal
            UserDTO userDTO = new UserDTO();
            userDTO.setId(userId);
            userDTO.setPhone(phone);
            UserHolder.saveUser(userDTO);

            return true;
        } catch (Exception e) {
            log.error("Token 解析失败", e);
            response.setStatus(401);
            response.setContentType("application/json;charset=utf-8");
            response.getWriter().write("{\"code\":401,\"message\":\"登录已过期\"}");
            return false;
        }
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) throws Exception {
        // 6. 请求结束后清理 ThreadLocal，防止内存泄漏
        UserHolder.removeUser();
    }
}




