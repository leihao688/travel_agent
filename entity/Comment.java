package org.example.travel_commend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 评论实体类（MVP 精简版）
 * 存储用户对景点的评价、评分、图片等
 */
@Data
@TableName("comment")
public class Comment implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 评论唯一ID（主键，自增）
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 发表评论的用户ID
     */
    private Long userId;

    /**
     * 被评论的景点ID
     */
    private Long attractionId;

    /**
     * 父评论ID（用于楼中楼回复功能）
     * 0: 顶级评论（直接评论景点）
     * >0: 回复其他用户的评论
     */
    private Long parentId;

    /**
     * 评分（1-5星）
     * 1: 非常差
     * 2: 较差
     * 3: 一般
     * 4: 较好
     * 5: 非常好
     */
    private Integer rating;

    /**
     * 评论内容文字
     */
    private String content;

    /**
     * 评论图片列表（JSON数组格式存储URL）
     */
    private String images;

    /**
     * 点赞数
     */
    private Integer likeCount = 0;

    /**
     * 评论状态（审核机制）
     * 0: 待审核（刚发布）
     * 1: 已通过（正常展示）
     * 2: 已拒绝（违规内容）
     */
    private Integer status = 1;
    /**
     * 根评论 ID
     * 0: 自己是根评论
     * >0: 属于哪个根评论的讨论区
     */
    private Long rootId;
    /**
     * 回复评论数
     */

    private Integer replyCount = 0;
    /**
     * 评论创建时间
     */


    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 评论更新时间（编辑评论时更新）
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