package org.example.travel_commend.Util;

import org.example.travel_commend.dto.UserDTO;

public class UserHolder {

    private static final ThreadLocal<UserDTO> tl = new ThreadLocal<>();

    public static void saveUser(UserDTO user) {
        tl.set(user);
    }

    public static UserDTO getUser() {
        return tl.get();
    }

    public static Long getUserId() {
        UserDTO user = tl.get();
        return user != null ? user.getId() : null;
    }

    public static void removeUser() {
        tl.remove();
    }
}
