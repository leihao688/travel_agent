package org.example.travel_commend.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.example.travel_commend.entity.User;

@Mapper
public interface UserMapper extends BaseMapper<User> {
}
