package org.example.travel_commend.Controller;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Service.AttCommentService;
import org.example.travel_commend.Service.LikeRecordService;
import org.example.travel_commend.VO.CommentVO;
import org.example.travel_commend.dto.CommentDTO;
import org.example.travel_commend.dto.CommentQueryDTO;
import org.example.travel_commend.dto.Result;
import org.springframework.web.bind.annotation.*;

@Slf4j
@RestController
@RequestMapping("/api/attraction/comment")
@RequiredArgsConstructor
@Tag(name = "景点评论管理", description = "景点评论与回复接口")
public class CommentController {
    private final AttCommentService commentService;
    private final LikeRecordService likeRecordService;
    @PostMapping
    @Operation(summary = "发布评论/回复")
    public Result<Void> createComment(@Valid @RequestBody CommentDTO commentDTO) {
        log.info("发布评论请求：{}", commentDTO);
        return commentService.createComment(commentDTO);
    }
    @GetMapping("/list")
    public Result<Page<CommentVO>> getAttractionComments(CommentQueryDTO queryDTO) {
        log.info("查看景点评论{}",queryDTO);
        return commentService.getAttractionComments(queryDTO);
    }

    @GetMapping("/replies")
    public Result<Page<CommentVO>> getCommentReplies(CommentQueryDTO queryDTO) {
        // 查子评论逻辑：where parent_id = ?
        return commentService.getCommentReplies(queryDTO);
    }
    @PostMapping("/like/{commentId}")
    @Operation(summary = "点赞/取消点赞", description = "切换评论点赞状态，已点赞则取消，未点赞则点赞")
    public Result<Void> toggleLike(@PathVariable Long commentId) {
        log.info("切换点赞状态：{}", commentId);
        return likeRecordService.toggleLike(commentId);
    }





}
