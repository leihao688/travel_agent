package org.example.travel_commend.Controller;


import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Service.UserService;

import org.example.travel_commend.Util.UserHolder;
import org.example.travel_commend.VO.UserVO;
import org.example.travel_commend.dto.*;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/user")
@Tag(name = "用户管理", description = "用户相关接口")
public class UserController {
    @Resource
    private UserService userService;

    @PostMapping("/code")
    @Operation(summary = "发送验证码", description = "向指定手机号发送6位数字验证码，有效期5分钟")
    public Result<String> sendCode(@RequestParam String phone) {
        log.info("发送验证码：{}", phone);
        return userService.sendCode(phone);
    }
    @PostMapping("/register")
    @Operation(summary = "用户注册", description = "使用手机号、验证码和密码完成用户注册")
    public Result<Void> register(@Valid @RequestBody UserRegisterDTO userRegisterDTO) {
        log.info("用户注册：{}", userRegisterDTO);
         return userService.register(userRegisterDTO);


    }

    @PostMapping("/login/code")
    @Operation(summary = "验证码登录", description = "使用手机号+验证码登录，返回JWT Token")
    public Result<String> loginByCode(
            @Parameter(description = "手机号", required = true) @RequestParam String phone,
            @Parameter(description = "验证码", required = true) @RequestParam String code) {
        log.info("验证码登录：{}", phone);
        return userService.loginByCode(phone, code);
    }

    @PostMapping("/login/password")
    @Operation(summary = "密码登录", description = "使用手机号+密码登录，返回JWT Token")
    public Result<String> loginByPassword(
            @Parameter(description = "手机号", required = true) @RequestParam String phone,
            @Parameter(description = "密码", required = true) @RequestParam String password) {
        log.info("密码登录：{}", phone);
        return userService.loginByPassword(phone, password);
    }
    @GetMapping("/test/auth")
    @Operation(summary = "测试登录态")
    public Result<String> testAuth() {
        Long userId = UserHolder.getUserId();
        return Result.success("当前登录用户 ID: " + userId);
    }
    @GetMapping("/info")
    @Operation(summary = "获取个人信息", description = "获取当前登录用户的详细信息")
    public Result<UserVO> getUserInfo() {
        log.info("获取个人信息");
        return userService.getUserInfo();
    }

    @PostMapping("/logout")
    @Operation(summary = "退出登录", description = "注销当前 Token，使设备下线")
    public Result<Void> logout() {
        log.info("退出登录");
        return userService.logout();
    }
    @PostMapping("/update")
    @Operation(summary = "更新用户信息", description = "更新当前登录用户的信息")
    public Result<Void> updateUserInfo(@Valid @RequestBody UserUpdateDTO userUpdateDTO) {
        log.info("更新用户信息：{}", userUpdateDTO);
        return userService.updateUserInfo(userUpdateDTO);
    }

}

