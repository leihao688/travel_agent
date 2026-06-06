package org.example.travel_commend.Controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Service.SignService;
import org.example.travel_commend.Util.UserHolder;
import org.example.travel_commend.VO.SignStatusVO;
import org.example.travel_commend.dto.Result;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@Slf4j
@RestController
@RequestMapping("/api/sign")
@RequiredArgsConstructor
@Tag(name = "签到管理", description = "用户签到相关接口")
public class SignController {
    private final SignService signService;

    @PostMapping
    @Operation(summary = "用户签到")
    public Result<Void> doSign() {
        log.info("用户签到");
        return signService.sign(UserHolder.getUserId());
    }

    @GetMapping("/status")
    @Operation(summary = "获取签到状态")
    public Result<SignStatusVO> getSignStatus() {
        log.info("获取签到状态");
        return signService.getSignStatus(UserHolder.getUserId());
    }

    @GetMapping("/month")
    @Operation(summary = "获取当月签到情况")
    public Result<boolean[]> getMonthSignDays(
            @RequestParam(required = false) Integer year,
            @RequestParam(required = false) Integer month) {
        log.info("获取当月签到情况 - year: {}, month: {}", year, month);
        LocalDate today = LocalDate.now();
        int y = year != null ? year : today.getYear();
        int m = month != null ? month : today.getMonthValue();
        return Result.success(signService.getMonthSignDays(UserHolder.getUserId(), y, m));
    }
}
