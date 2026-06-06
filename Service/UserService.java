package org.example.travel_commend.Service;

import com.baomidou.mybatisplus.extension.service.IService;
import jakarta.validation.Valid;
import org.example.travel_commend.VO.UserVO;
import org.example.travel_commend.dto.*;
import org.example.travel_commend.entity.User;

public interface UserService extends IService<User>  {
    Result<Void> register(UserRegisterDTO userRegisterDTO);

    Result<String> sendCode(String phone);

    

    Result<String> loginByCode(String phone, String code);

    Result<String> loginByPassword(String phone, String password);

    Result<UserVO> getUserInfo();

    Result<Void> logout();

    Result<Void> updateUserInfo(@Valid UserUpdateDTO userUpdateDTO);
}
