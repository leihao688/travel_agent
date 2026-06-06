package org.example.travel_commend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

/**
 * 用户注册 DTO
 */
@Data
public class UserRegisterDTO {
    /**
     * 手机号（必填，用于登录和接收验证码）
     */
    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;

    /**
     * 密码（必填，用于登录）
     */
    @NotBlank(message = "密码不能为空")
    private String password;

    /**
     * 短信验证码（必填，验证手机真实性）
     */
    @NotBlank(message = "验证码不能为空")
    private String code;

    /**
     * 邮箱（可选，用于找回密码）
     */
    private String email;

    /**
     * 昵称（可选，注册时可设置）
     */
    private String nickname;
}
