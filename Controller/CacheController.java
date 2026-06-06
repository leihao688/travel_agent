package org.example.travel_commend.Controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.example.travel_commend.Util.MultiLevelCacheClient;
import org.example.travel_commend.dto.Result;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/cache")
@RequiredArgsConstructor
@Tag(name = "缓存管理", description = "缓存监控和管理接口")
public class CacheController {
    private final MultiLevelCacheClient multiLevelCache;

    @GetMapping("/stats")
    @Operation(summary = "获取缓存统计信息")
    public Result<String> getCacheStats() {
        String stats = multiLevelCache.getCacheStats();
        return Result.success(stats);
    }

    @DeleteMapping("/invalidate/{key}")
    @Operation(summary = "清除指定缓存")
    public Result<Void> invalidateCache(@PathVariable String key) {
        multiLevelCache.invalidate(key);
        return Result.success();
    }
}
