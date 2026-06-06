package org.example.travel_commend.VO;

import lombok.Data;

@Data
public class SignStatusVO {
    private boolean isSignedToday;
    private int continuousDays;
    private int monthCount;
}
