
package org.example.travel_commend.VO;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Schema(description = "景点信息视图对象")
public class AttractionVO implements Serializable {

    @Schema(description = "景点ID", example = "1")
    private Long id;

    @Schema(description = "景点名称", example = "故宫博物院")
    private String name;

    @Schema(description = "景点介绍", example = "中国明清两代的皇家宫殿...")
    private String description;

    @Schema(description = "景点分类", example = "5A")
    private String category;

    @Schema(description = "子分类", example = "人文历史")
    private String subCategory;

    @Schema(description = "平均评分", example = "4.8")
    private BigDecimal rating;

    @Schema(description = "评分总数", example = "12580")
    private Integer ratingCount;

    @Schema(description = "评论总数", example = "8965")
    private Integer commentCount;

    @Schema(description = "门票价格(元)", example = "60.00")
    private BigDecimal price;

    @Schema(description = "所在省份", example = "北京市")
    private String province;

    @Schema(description = "所在城市", example = "北京市")
    private String city;

    @Schema(description = "所在区县", example = "东城区")
    private String district;

    @Schema(description = "详细地址", example = "景山前街4号")
    private String address;

    @Schema(description = "开放时间", example = "08:30-17:00")
    private String openTime;

    @Schema(description = "联系电话", example = "010-85007421")
    private String phone;

    @Schema(description = "景点图片列表(JSON数组)")
    private List<String> images;

    @Schema(description = "浏览量", example = "125800")
    private Integer viewCount;

    @Schema(description = "收藏数", example = "5680")
    private Integer favoriteCount;

    @Schema(description = "创建时间")
    private LocalDateTime createTime;
}
