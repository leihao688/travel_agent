package org.example.travel_commend.Service;

import org.example.travel_commend.VO.SignStatusVO;
import org.example.travel_commend.dto.Result;

public interface SignService {

    /**
     * 用户签到
     */
    Result<Void> sign(Long userId);

    /**
     * 检查用户当天是否已签到
     */
    boolean isSignedToday(Long userId);

    /**
     * 获取用户本月签到天数
     */
    int getMonthSignCount(Long userId);

    /**
     * 获取用户连续签到天数
     */
    int getContinuousSignDays(Long userId);

    /**
     * 获取用户签到位图
     */
    String getSignBitmap(Long userId);

    /**
     * 获取指定月份的签到情况
     */
    boolean[] getMonthSignDays(Long userId, int year, int month);

    /**
     * 获取签到状态
     */
    Result<SignStatusVO> getSignStatus(Long userId);
}
