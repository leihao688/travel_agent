package org.example.travel_commend.Controller;

import cn.hutool.db.PageResult;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.annotation.Resource;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Service.AttractionService;
import org.example.travel_commend.VO.AttractionVO;
import org.example.travel_commend.annotation.AdminRequired;
import org.example.travel_commend.dto.AttractionDTO;
import org.example.travel_commend.dto.AttractionQueryDTO;
import org.example.travel_commend.dto.Result;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/attraction")
@Tag(name = "景点管理", description = "景点相关接口")
public class AttractionController {

    @Resource
    private AttractionService attractionService;

    @PostMapping
    @AdminRequired
    @Operation(summary = "创建景点", description = "【管理员】创建新景点信息")
    public Result<Void> createAttraction(@Valid @RequestBody AttractionDTO attractionDTO) {
        log.info("创建景点：{}", attractionDTO.getName());
        return attractionService.createAttraction(attractionDTO);
    }

    @PutMapping("/{id}")
    @AdminRequired
    @Operation(summary = "更新景点", description = "【管理员】更新指定景点的信息")
    public Result<Void> updateAttraction(
            @Parameter(description = "景点ID", required = true) @PathVariable Long id,
            @Valid @RequestBody AttractionDTO attractionDTO) {
        log.info("更新景点 - ID: {}", id);
        return attractionService.updateAttraction(id, attractionDTO);
    }

    @DeleteMapping("/{id}")
    @AdminRequired
    @Operation(summary = "删除景点", description = "【管理员】逻辑删除指定景点")
    public Result<Void> deleteAttraction(
            @Parameter(description = "景点ID", required = true) @PathVariable Long id) {
        log.info("删除景点 - ID: {}", id);
        return attractionService.deleteAttraction(id);
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取景点详情", description = "根据ID获取景点详细信息(所有人可访问)")
    public Result<AttractionVO> getAttraction(
            @Parameter(description = "景点ID", required = true) @PathVariable Long id) {
        log.info("获取景点详情 - ID: {}", id);

        attractionService.increaseViewCount(id);

        return attractionService.getAttractionById(id);
    }

    @GetMapping("/list")
    @Operation(summary = "查询景点列表", description = "支持多条件筛选、分页、排序查询景点(所有人可访问)")
    public Result<Page<AttractionVO>> queryAttractions(AttractionQueryDTO queryDTO) {
        log.info("查询景点列表 - 参数: {}", queryDTO);
        return attractionService.queryAttractions(queryDTO);
    }

    @GetMapping("/hot")
    @Operation(summary = "获取热门景点", description = "获取热门景点 TOP10（按评分人数和平均分加权排序）")
    public Result<List<AttractionVO>> getHotAttractions() {
        log.info("获取热门景点列表");
        return attractionService.getHotAttractions();
    }

}
