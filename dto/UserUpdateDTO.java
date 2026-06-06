package org.example.travel_commend.dto;

import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
public class UserUpdateDTO {
    /**
     * 用户昵称（展示名称）
     */
    private String nickname;

    /**
     * 用户头像URL
     */
    private String avatar;

    /**
     * 个人简介/签名
     */
    private String bio;

    /**
     * 邮箱地址
     */
    @Pattern(regexp = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", message = "邮箱格式不正确")
    private String email;

    /**
     * 手机号
     */
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;}
