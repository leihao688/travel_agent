package org.example.travel_commend.Config;

import cn.hutool.core.util.StrUtil;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Mapper.UserMapper;
import org.example.travel_commend.Util.JwtUtil;
import org.example.travel_commend.Util.RedisConstants;
import org.example.travel_commend.Util.UserHolder;
import org.example.travel_commend.dto.UserDTO;
import org.example.travel_commend.entity.User;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * JWT 认证过滤器 - 替代原来的 LoginInterceptor
 * 工作原理：
 * 1. 从请求头中获取 Authorization 字段（包含 JWT token）
 * 2. 解析 token，验证签名是否正确
 * 3. 检查 Redis 中 token 是否存在且有效（防止 token 被盗用）
 * 4. 有效则将用户信息存入 SecurityContext，供后续代码使用
 * 5. 无效或过期则放行，由 SecurityConfig 判断是否需要登录
 * 为什么用过滤器而不是拦截器？
 * - 过滤器在 Servlet 层更早拦截请求，安全性更好
 * - Spring Security 原生支持过滤器链，方便扩展
 * - 可以享受 Security 提供的更多安全功能
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtUtil jwtUtil;
    private final StringRedisTemplate stringRedisTemplate;
    private final UserMapper userMapper;

    /**
     * 核心过滤方法 - 每个请求都会执行一次
     *
     * @param request     HTTP 请求对象
     * @param response    HTTP 响应对象
     * @param filterChain 过滤器链 - 决定是否继续往下执行
     */
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        // ========== 步骤1：从请求头获取 Token ==========
        String token = request.getHeader("Authorization");

        // 如果没有 Token，直接放行（可能是公开接口）
        if (StrUtil.isBlank(token)) {
            filterChain.doFilter(request, response);
            return;
        }

        // ========== 步骤2：处理 Token 格式 ==========
        // 前端通常这样传递: Bearer eyJhbGciOiJIUzI1NiJ9...
        // 需要去掉 "Bearer " 前缀，只保留 token 本体
        if (token.startsWith("Bearer ")) {
            token = token.substring(7);
        }

        try {
            // ========== 步骤3：解析 JWT Token ==========
            // 解析失败会抛出 JwtException，说明 token 被篡改或过期
            Claims claims = jwtUtil.parseToken(token);
            Long userId = Long.parseLong(claims.getSubject());
            String phone = claims.get("phone", String.class);

            // ========== 步骤4：验证 Redis 中的 Token ==========
            // 即使 JWT 有效，也要检查 Redis 中是否还存在（可能已被主动登出）
            String redisKey = RedisConstants.LOGIN_USER_KEY + phone;
            String savedToken = stringRedisTemplate.opsForValue().get(redisKey);

            // Redis 中没有 token 或 token 不匹配，说明登录已失效
            if (StrUtil.isBlank(savedToken) || !savedToken.equals(token)) {
                filterChain.doFilter(request, response);
                return;
            }

            // ========== 步骤5：刷新 Token 有效期（续期） ==========
            // 用户每操作一次，就延长 24 小时，避免频繁登录
            stringRedisTemplate.expire(redisKey, RedisConstants.LOGIN_USER_TTL, TimeUnit.HOURS);

            // ========== 步骤6：从数据库获取用户信息（包括角色） ==========
            User user = userMapper.selectById(userId);

            // ========== 步骤7：保存用户信息到 UserHolder ==========
            // 用于在 Service/Controller 层通过 UserHolder.getUserId() 获取当前登录用户
            UserDTO userDTO = new UserDTO();
            userDTO.setId(userId);
            userDTO.setPhone(phone);
            userDTO.setRole(user.getRole());
            UserHolder.saveUser(userDTO);

            // ========== 步骤8：存入 SecurityContext ==========
            // 这是 Spring Security 标准的用户认证方式
            // 根据用户角色设置权限
            List<SimpleGrantedAuthority> authorities = new ArrayList<>();
            authorities.add(new SimpleGrantedAuthority("ROLE_USER"));
            if (user.getRole() != null && user.getRole() == 1) {
                authorities.add(new SimpleGrantedAuthority("ROLE_ADMIN"));
            }

            UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                    userId, // 用户标识
                    null, // 凭证（过滤器阶段为空）
                    authorities // 权限列表
            );

            // 将认证信息存入 Security 上下文，后续 Security 框架会自动使用
            SecurityContextHolder.getContext().setAuthentication(authentication);

            // ========== 步骤8：继续执行过滤器链 ==========
            // 放行请求，让请求继续流向下一个过滤器或 Controller
            filterChain.doFilter(request, response);

        } catch (JwtException e) {
            // ========== 异常处理：Token 解析失败 ==========
            // 可能是伪造的 token、篡改的 token、或者过期的 token
            log.error("JWT 解析失败: {}", e.getMessage());
            // 解析失败也放行，让 SecurityConfig 的 .authenticated() 配置来决定是否拒绝
            filterChain.doFilter(request, response);
        } finally {
            // ========== 清理工作 ==========
            // 请求结束后清理 ThreadLocal，防止内存泄漏
            // 因为 UserHolder 使用 ThreadLocal 存储用户信息
            UserHolder.removeUser();
        }
    }
}