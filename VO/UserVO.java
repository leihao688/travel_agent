package org.example.travel_commend.VO;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class UserVO {

    private Long id;
    private String username;
    private String phone;
    private String email;
    private String avatar;
    private String nickname;
    private String bio;
    private Integer level;
    private String levelName;
    private String levelColor;
    private Integer exp;
    private Integer expNeeded;
    private Integer levelProgress;
    private LocalDateTime createTime;

    // 不包含：password, deleted, status, updateTime
}
