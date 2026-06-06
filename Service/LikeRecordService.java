package org.example.travel_commend.Service;

import com.baomidou.mybatisplus.extension.service.IService;

import org.example.travel_commend.dto.Result;
import org.example.travel_commend.entity.LikeRecord;

import java.util.List;
import java.util.Set;

public interface LikeRecordService extends IService<LikeRecord> {


    Result<Void> toggleLike(Long commentId);

    boolean isLiked(Long userId,Long commentId);

    Set<Long> getUserLikedComments(Long userId, List<Long> commentIds);

    void syncLikeDataToMySQL();


}
