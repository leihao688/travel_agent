package org.example.travel_commend.Service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import jakarta.validation.Valid;
import org.example.travel_commend.VO.AttractionVO;
import org.example.travel_commend.VO.CommentVO;
import org.example.travel_commend.dto.CommentDTO;
import org.example.travel_commend.dto.CommentQueryDTO;
import org.example.travel_commend.dto.Result;

import org.example.travel_commend.entity.Comment;
import org.springframework.stereotype.Service;


public interface AttCommentService extends IService<Comment> {
    Result<Void> createComment(@Valid CommentDTO commentDTO);

  

    Result<Page<CommentVO>> getAttractionComments(CommentQueryDTO commentQueryDTO);

    Result<Page<CommentVO>> getCommentReplies(CommentQueryDTO commentQueryDTO);


}
