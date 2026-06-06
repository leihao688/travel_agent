package org.example.travel_commend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.io.Serializable;

@Data
@Schema(description = "评论发布请求")
public class CommentDTO implements Serializable {

    @Schema(description = "景点ID")
    private Long attractionId;

    @Schema(description = "父评论ID（0或不传表示顶级评论）")
    private Long parentId;

    @Min(value = 1, message = "评分至少1星")
    @Max(value = 5, message = "评分最多5星")
    @Schema(description = "评分（1-5星），顶级评论必填")
    private Integer rating;

    @NotBlank(message = "评论内容不能为空")
    @Schema(description = "评论内容")
    private String content;

    @Schema(description = "评论图片列表（JSON数组）")
    private String images;
}
