package org.example.travel_commend.Interceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.annotation.AdminRequired;
import org.example.travel_commend.dto.UserDTO;
import org.example.travel_commend.Util.UserHolder;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

/**
 * 管理员权限拦截器
 * 检查带有 @AdminRequired 注解的接口是否有管理员权限
 */
@Slf4j
@Component
public class AdminInterceptor implements HandlerInterceptor {

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 如果不是方法处理，直接放行
        if (!(handler instanceof HandlerMethod)) {
            return true;
        }

        HandlerMethod handlerMethod = (HandlerMethod) handler;
        
        // 检查方法是否有 @AdminRequired 注解
        AdminRequired adminRequired = handlerMethod.getMethodAnnotation(AdminRequired.class);
        if (adminRequired == null) {
            // 没有注解，直接放行
            return true;
        }

        // 获取当前用户
        UserDTO user = UserHolder.getUser();
        if (user == null) {
            // 未登录
            response.setStatus(HttpStatus.UNAUTHORIZED.value());
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":401,\"msg\":\"请先登录\"}");
            return false;
        }

        // 检查角色是否为管理员
        if (user.getRole() == null || user.getRole() != 1) {
            // 不是管理员
            response.setStatus(HttpStatus.FORBIDDEN.value());
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"code\":403,\"msg\":\"权限不足，需要管理员权限\"}");
            log.warn("用户 {} 尝试访问管理员接口，但不是管理员", user.getId());
            return false;
        }

        // 是管理员，放行
        log.info("管理员 {} 访问管理员接口", user.getId());
        return true;
    }
}