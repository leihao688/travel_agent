package org.example.travel_commend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 景点实体类（MVP 版本）
 */
@Data
@TableName("attraction")
public class Attraction implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 景点唯一ID（主键，自增）
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 景点名称
     */
    private String name;

    /**
     * 景点详细介绍
     */
    private String description;

    /**
     * 景点分类（5A/4A/自然风光/人文历史/主题乐园等）
     */
    private String category;

    /**
     * 子分类（如：博物馆、寺庙、海滨、山脉等）
     */
    private String subCategory;

    // ========== 评分相关 ==========

    /**
     * 平均评分缓存（0-5分，保留1位小数）
     * 由定时任务根据评论动态计算更新
     */
    private BigDecimal rating;

    /**
     * 评分总数（用于计算平均分）
     */
    private Integer ratingCount;

    /**
     * 评论总数
     */
    private Integer commentCount;

    // ========== 价格与位置 ==========

    /**
     * 门票价格（单位：元）
     */
    private BigDecimal price;

    /**
     * 所在省份
     */
    private String province;

    /**
     * 所在城市
     */
    private String city;

    /**
     * 所在区县
     */
    private String district;

    /**
     * 详细地址
     */
    private String address;

    // ========== 开放信息 ==========

    /**
     * 开放时间（如：08:00-18:00）
     */
    private String openTime;

    /**
     * 联系电话
     */
    private String phone;

    /**
     * 景点图片列表（JSON数组格式存储URL）
     */
    private String images;

    // ========== 统计数据 ==========

    /**
     * 浏览量（访问次数）
     */
    private Integer viewCount;

    /**
     * 收藏数
     */
    private Integer favoriteCount;

    /**
     * 景点状态
     * 0: 下架（暂停展示）
     * 1: 上架（正常展示）
     */
    private Integer status;

    // ========== 系统字段 ==========

    /**
     * 创建时间（首次录入时自动填充）
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
     * 0: 未删除
     * 1: 已删除
     */
    @TableLogic
    private Integer deleted;
}
