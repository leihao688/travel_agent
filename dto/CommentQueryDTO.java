package org.example.travel_commend.dto;


import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;

@Data
@Schema(description = "评论查询参数")
public class CommentQueryDTO implements Serializable {

    @Schema(description = "景点ID（查询某景点的评论）")
    private Long attractionId;


    @Schema(description = "父评论ID（查询某条评论的回复）")
    private Long parentId;

    @Schema(description = "该评论ID（查询某条评论的回复）")
    private Long id;

    @Schema(description = "页码", example = "1")
    private Integer pageNum = 1;

    @Schema(description = "每页数量", example = "10")
    private Integer pageSize = 10;

    @Schema(description = "排序方式(createTime-时间,likeCount-热度)", example = "createTime")
    private String sortBy = "createTime";
}
