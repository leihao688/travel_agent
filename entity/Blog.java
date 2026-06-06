package org.example.travel_commend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 博客/游记实体类
 */
@Data
@TableName("blog")
public class Blog implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 博客唯一ID（主键，自增）
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 发布博客的用户ID
     */
    private Long userId;

    /**
     * 关联的景点ID（可选）
     */
    private Long attractionId;

    /**
     * 博客标题
     */
    private String title;

    /**
     * 博客正文内容
     */
    private String content;

    /**
     * 博客图片列表（JSON数组格式存储URL）
     */
    private String images;

    /**
     * 浏览量
     */
    private Integer viewCount;

    /**
     * 点赞数
     */
    private Integer likeCount;

    /**
     * 评论数
     */
    private Integer commentCount;

    /**
     * 博客状态
     * 0: 草稿
     * 1: 已发布
     */
    private Integer status;

    /**
     * 创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 更新时间
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
