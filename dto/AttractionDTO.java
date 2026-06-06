package org.example.travel_commend.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;

@Data
@Schema(description = "景点创建/更新请求")
public class AttractionDTO implements Serializable {

    @NotBlank(message = "景点名称不能为空")
    @Schema(description = "景点名称", example = "故宫博物院")
    private String name;

    @Schema(description = "景点详细介绍", example = "中国明清两代的皇家宫殿...")
    private String description;

    @Schema(description = "景点分类", example = "5A")
    private String category;

    @Schema(description = "子分类", example = "人文历史")
    private String subCategory;

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

    @Schema(description = "景点图片列表(JSON数组)", example = "[\"url1\",\"url2\"]")
    private String images;
}