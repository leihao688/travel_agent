package org.example.travel_commend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;

@Data
@Schema(description = "景点查询参数")
public class AttractionQueryDTO implements Serializable {

    @Schema(description = "关键词搜索", example = "故宫")
    private String keyword;

    @Schema(description = "景点分类", example = "5A")
    private String category;

    @Schema(description = "子分类", example = "博物馆")
    private String subCategory;

    @Schema(description = "省份", example = "北京市")
    private String province;

    @Schema(description = "城市", example = "北京市")
    private String city;

    @Schema(description = "最低价格", example = "0")
    private Integer minPrice;

    @Schema(description = "最高价格", example = "200")
    private Integer maxPrice;

    @Schema(description = "排序方式(rating-评分,price-价格,viewCount-浏览量)", example = "rating")
    private String sortBy;

    @Schema(description = "页码", example = "1")
    private Integer pageNum = 1;

    @Schema(description = "每页数量", example = "10")
    private Integer pageSize = 10;
}