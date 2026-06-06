package org.example.travel_commend.Util;

import java.util.regex.Pattern;

public class RegexUtils {
    private static final Pattern MOBILE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

    private static final Pattern EMAIL_PATTERN = Pattern.compile("^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\\.[a-zA-Z0-9_-]+)+$");

    private static final Pattern ID_CARD_PATTERN = Pattern.compile("^(\\d{17}[0-9Xx]|\\d{15})$");

    private static final Pattern USERNAME_PATTERN = Pattern.compile("^[a-zA-Z0-9_\\u4e00-\\u9fa5]{2,20}$");

    private static final Pattern PASSWORD_PATTERN = Pattern.compile("^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,20}$");

    private static final Pattern URL_PATTERN = Pattern.compile("^(https?://)?([a-zA-Z0-9-]+\\.)+[a-zA-Z]{2,}(/.*)?$");

    private static final Pattern IP_PATTERN = Pattern.compile("^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$");

    private static final Pattern POSTAL_CODE_PATTERN = Pattern.compile("^[0-9]{6}$");

    private static final Pattern CAR_NUMBER_PATTERN = Pattern.compile("^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]$");

    public static boolean isMobile(String mobile) {
        if (mobile == null || mobile.isEmpty()) {
            return false;
        }
        return MOBILE_PATTERN.matcher(mobile).matches();
    }

    public static boolean isEmail(String email) {
        if (email == null || email.isEmpty()) {
            return false;
        }
        return EMAIL_PATTERN.matcher(email).matches();
    }

    public static boolean isIdCard(String idCard) {
        if (idCard == null || idCard.isEmpty()) {
            return false;
        }
        return ID_CARD_PATTERN.matcher(idCard).matches();
    }

    public static boolean isUsername(String username) {
        if (username == null || username.isEmpty()) {
            return false;
        }
        return USERNAME_PATTERN.matcher(username).matches();
    }

    public static boolean isPassword(String password) {
        if (password == null || password.isEmpty()) {
            return false;
        }
        return PASSWORD_PATTERN.matcher(password).matches();
    }

    public static boolean isUrl(String url) {
        if (url == null || url.isEmpty()) {
            return false;
        }
        return URL_PATTERN.matcher(url).matches();
    }

    public static boolean isIp(String ip) {
        if (ip == null || ip.isEmpty()) {
            return false;
        }
        return IP_PATTERN.matcher(ip).matches();
    }

    public static boolean isPostalCode(String postalCode) {
        if (postalCode == null || postalCode.isEmpty()) {
            return false;
        }
        return POSTAL_CODE_PATTERN.matcher(postalCode).matches();
    }

    public static boolean isCarNumber(String carNumber) {
        if (carNumber == null || carNumber.isEmpty()) {
            return false;
        }
        return CAR_NUMBER_PATTERN.matcher(carNumber).matches();
    }
}

