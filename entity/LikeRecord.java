package org.example.travel_commend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 点赞记录实体类
 * 记录用户对评论的点赞行为（防止重复点赞）
 */
@Data
@TableName("like_record")
public class LikeRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 点赞记录唯一ID（主键，自增）
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 点赞用户ID
     */
    private Long userId;

    /**
     * 被点赞的评论ID
     */
    private Long commentId;

    /**
     * 点赞时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;
}
