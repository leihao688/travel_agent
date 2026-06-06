package org.example.travel_commend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@TableName("user")
public class User implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 用户唯一ID（主键，自增）
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 用户名（用于登录）
     */
    private String username;

    /**
     * 密码（BCrypt加密存储）
     */
    private String password;

    /**
     * 手机号（可用于登录）
     */
    private String phone;

    /**
     * 邮箱地址（可用于登录或找回密码）
     */
    private String email;

    /**
     * 用户头像URL
     */
    private String avatar;

    /**
     * 用户昵称（展示名称）
     */
    private String nickname;

    /**
     * 个人简介/签名
     */
    private String bio;

    /**
     * 用户等级（1-5级，基于活跃度和贡献度）
     * 1: 新用户
     * 2: 活跃用户
     * 3: 优质用户
     * 4: 资深用户
     * 5: 核心用户
     */
    private Integer level = 1;

    /**
     * 用户经验值
     * 用于计算等级升级
     */
    private Integer exp = 0;

    /**
     * 今日获取经验值（用于限制每日上限）
     */
    private Integer todayExp = 0;

    /**
     * 最后登录日期（用于连续登录奖励）
     */
    private LocalDateTime lastLoginDate;

    /**
     * 用户角色
     * 0: 普通用户
     * 1: 管理员
     */
    private Integer role = 0;

    /**
     * 账号状态
     * 0: 禁用/封禁
     * 1: 正常
     */
    private Integer status;

    /**
     * 创建时间（首次注册时自动填充）
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 更新时间（插入和更新时自动填充）
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /**
     * 逻辑删除标志
     * 0: 未删除（正常状态）
     * 1: 已删除（逻辑删除，数据保留在数据库中）
     */
    @TableLogic
    private Integer deleted;
}
