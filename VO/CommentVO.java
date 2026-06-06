package org.example.travel_commend.VO;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

@Data
@Schema(description = "评论信息视图对象")
public class CommentVO implements Serializable {

    @Schema(description = "评论ID")
    private Long id;

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "用户昵称")
    private String userName;

    @Schema(description = "用户头像")
    private String userAvatar;

    @Schema(description = "景点ID")
    private Long attractionId;

    @Schema(description = "父评论ID（0表示顶级评论）")
    private Long parentId;

    @Schema(description = "评分（1-5星）")
    private Integer rating;

    @Schema(description = "评论内容")
    private String content;

    @Schema(description = "评论图片列表")
    private String images;

    @Schema(description = "点赞数")
    private Integer likeCount;

    @Schema(description = "是否已点赞（当前用户）")
    private Boolean isLiked;

    @Schema(description = "回复数量")
    private Integer replyCount;

    @Schema(description = "评论时间")
    private LocalDateTime createTime;
}
