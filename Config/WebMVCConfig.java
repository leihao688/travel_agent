package org.example.travel_commend.Config;

import lombok.RequiredArgsConstructor;
import org.example.travel_commend.Interceptor.AdminInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@RequiredArgsConstructor
public class WebMVCConfig implements WebMvcConfigurer {

    private final AdminInterceptor adminInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // 注册管理员权限拦截器
        registry.addInterceptor(adminInterceptor)
                .addPathPatterns("/**"); // 拦截所有请求
    }
}

