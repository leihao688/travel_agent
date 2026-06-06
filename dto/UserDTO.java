package org.example.travel_commend.dto;

import lombok.Data;

@Data
public class UserDTO {
    private Long id;
    private String nickname;
    private String icon;
    private String phone;
    private String bio;
    private Integer role;
}
