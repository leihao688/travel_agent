package org.example.travel_commend.Service;

import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import jakarta.annotation.PostConstruct;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Mapper.AttrCommentMapper;
import org.example.travel_commend.entity.Comment;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Set;

import static org.example.travel_commend.Util.RedisConstants.*;

@Service
@Slf4j
@RequiredArgsConstructor
public class CommentNotificationConsumer extends ServiceImpl<AttrCommentMapper, Comment> {

    private final MessageQueueService messageQueueService;
    private final StringRedisTemplate stringRedisTemplate;

    /**
     * 启动时从 MySQL 真实子评论数同步到 Redis（修复历史脏数据）
     * 不用 reply_count 字段（这个字段可能是脏数据），直接 count 真实子评论数
     */
    @PostConstruct
    public void initReplyCountFromDB() {
        log.info("开始从 MySQL 真实子评论数同步到 Redis...");

        // ⭐ Bug修复：先修复 root_id 错误的顶级评论（历史脏数据）
        List<Comment> topComments = lambdaQuery()
                .eq(Comment::getParentId, 0)
                .list();
        int reallyFixed = 0;
        for (Comment c : topComments) {
            if (c.getRootId() == null || c.getRootId() == 0 || !c.getRootId().equals(c.getId())) {
                c.setRootId(c.getId());
                updateById(c);
                reallyFixed++;
                log.info("修复顶级评论 root_id: id={}, root_id={}", c.getId(), c.getId());
            }
        }
        log.info("顶级评论 root_id 修复完成，共修复 {} 条", reallyFixed);

        List<Comment> topLevelComments = lambdaQuery()
                .eq(Comment::getParentId, 0)
                .eq(Comment::getStatus, 1)
                .list();
        for (Comment c : topLevelComments) {
            String key = COMMENT_REPLY_COUNT_KEY + c.getId();
            // ⭐ 直接 count 真实子评论数（忽略 reply_count 字段的脏数据）
            Long realReplyCount = lambdaQuery()
                    .eq(Comment::getRootId, c.getId())
                    .ne(Comment::getParentId, 0)
                    .eq(Comment::getStatus, 1)
                    .count();
            int realCount = realReplyCount == null ? 0 : realReplyCount.intValue();
            stringRedisTemplate.opsForValue().set(key, String.valueOf(realCount));
            log.info("同步评论 {} 的真实回复数：count={}", c.getId(), realCount);
        }
        log.info("历史回复数同步完成，共处理 {} 条顶级评论", topLevelComments.size());

        // ⭐ Bug修复：启动时重新计算所有顶级评论的热度分数
        log.info("开始重新计算热门排行榜分数...");
        for (Comment c : topLevelComments) {
            recalculateHotScore(c);
        }
        log.info("热门排行榜分数重新计算完成");
    }

    /**
     * 重新计算单个评论的热度分数
     */
    private void recalculateHotScore(Comment comment) {
        if (comment == null || comment.getAttractionId() == null) {
            return;
        }
        String hotKey = ATTRACTION_HOT_COMMENTS_KEY + comment.getAttractionId();
        // ⭐ Bug修复：启动时先清理 ZSet 中所有分数 <= 0 的历史脏数据成员
        cleanupZeroScoreMembers(hotKey);
        // 优先用 Redis 的点赞数，没有再用 MySQL
        String countKey = COMMENT_LIKE_COUNT_KEY + comment.getId();
        String likeCountStr = stringRedisTemplate.opsForValue().get(countKey);
        int likeCount;
        if (likeCountStr != null) {
            likeCount = Integer.parseInt(likeCountStr);
        } else {
            likeCount = comment.getLikeCount() == null ? 0 : comment.getLikeCount();
        }
        // 用 Redis 的实时回复数
        String replyCountKey = COMMENT_REPLY_COUNT_KEY + comment.getId();
        String replyCountStr = stringRedisTemplate.opsForValue().get(replyCountKey);
        int replyCount = replyCountStr != null ? Integer.parseInt(replyCountStr) : 0;
        // 计算热度分数
        double hotScore = calculateAdvancedHotScore(likeCount, replyCount, comment.getCreateTime());
        // ⭐ Bug修复：删除分数为 0 的 ZSet 成员（无效数据）
        if (hotScore <= 0) {
            stringRedisTemplate.opsForZSet().remove(hotKey, comment.getId().toString());
            log.info("删除无效热度数据: commentId={}", comment.getId());
            return;
        }
        stringRedisTemplate.opsForZSet().add(hotKey, comment.getId().toString(), hotScore);
        log.info("重算评论 {} 热度: likeCount={}, replyCount={}, score={}",
                comment.getId(), likeCount, replyCount, hotScore);
    }

    /**
     * 清理 ZSet 中所有分数 <= 0 的历史脏数据成员
     */
    private void cleanupZeroScoreMembers(String hotKey) {
        try {
            Set<ZSetOperations.TypedTuple<String>> allMembers = stringRedisTemplate
                    .opsForZSet().rangeWithScores(hotKey, 0, -1);
            if (allMembers == null || allMembers.isEmpty()) {
                return;
            }
            int cleanedCount = 0;
            for (ZSetOperations.TypedTuple<String> member : allMembers) {
                if (member.getScore() != null && member.getScore() <= 0 && member.getValue() != null) {
                    stringRedisTemplate.opsForZSet().remove(hotKey, member.getValue());
                    cleanedCount++;
                    log.info("清理 ZSet 脏数据: hotKey={}, commentId={}, score={}",
                            hotKey, member.getValue(), member.getScore());
                }
            }
            if (cleanedCount > 0) {
                log.info("ZSet 脏数据清理完成: hotKey={}, 共清理 {} 条", hotKey, cleanedCount);
            }
        } catch (Exception e) {
            log.error("清理 ZSet 脏数据失败: hotKey={}, 错误: {}", hotKey, e.getMessage(), e);
        }
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CommentNotification {
        private Long commentId;
        private Long userId;
        private Long attractionId;
        private String content;
        private Integer rating;
        private Long parentId;
        private String type;
    }

    @Scheduled(fixedDelay = 100)
    public void listenQueue() {
        String message = messageQueueService.receiveMessageNonBlocking(
                MessageQueueService.COMMENT_NOTIFICATION_QUEUE);

        if (message != null) {
            processMessage(message);
        }
    }

    private void processMessage(String message) {
        try {
            CommentNotification notification = JSONUtil.toBean(message, CommentNotification.class);
            log.info("收到消息: {}", message);

            Comment comment = new Comment();
            comment.setUserId(notification.getUserId());
            comment.setAttractionId(notification.getAttractionId());
            comment.setContent(notification.getContent());
            comment.setRating(notification.getRating());
            comment.setParentId(notification.getParentId() == null ? 0L : notification.getParentId());

            boolean isTopLevel = (notification.getParentId() == null || notification.getParentId() == 0);

            if (isTopLevel) {
                // ⭐ Bug修复：顶级评论的 rootId 等于自己的 id
                // 先保存获取 id，再回填 rootId
                comment.setRootId(0L);
            } else {
                // ⭐ Bug修复：递归查询真正的顶级评论ID（rootId）
                Long parentId = notification.getParentId();
                Long realRootId = findRootCommentId(parentId);
                comment.setRootId(realRootId);
                log.info("子评论入库 - parentId={}, realRootId={}", parentId, realRootId);
            }

            comment.setCreateTime(java.time.LocalDateTime.now());

            if (!save(comment)) {
                log.error("评论入库失败: userId={}, attractionId={}", notification.getUserId(),
                        notification.getAttractionId());
                return;
            }

            log.info("评论入库成功: commentId={}", comment.getId());

            if (isTopLevel) {
                boolean updated = lambdaUpdate().eq(Comment::getId, comment.getId())
                        .set(Comment::getRootId, comment.getId()).update();
                log.info("顶级评论回填 rootId: commentId={}, rootId={}, updated={}",
                        comment.getId(), comment.getId(), updated);
                addCommentToHotRank(comment);
            } else {
                Long rootId = comment.getRootId();
                if (rootId == null || rootId == 0)
                    rootId = comment.getId();
                // ⭐ Bug修复：先在Redis中实时更新回复数（用于前端显示）
                String replyCountKey = COMMENT_REPLY_COUNT_KEY + rootId;
                Long newReplyCount = stringRedisTemplate.opsForValue().increment(replyCountKey);
                log.info("Redis 回复数更新: rootId={}, count={}", rootId, newReplyCount);
                // 异步更新 MySQL 的 reply_count
                lambdaUpdate().eq(Comment::getId, rootId).setSql("reply_count = reply_count + 1").update();
                updateParentHotScore(rootId, comment.getAttractionId(), newReplyCount.intValue());
            }

            String listCacheKey = COMMENT_LIST_KEY + comment.getAttractionId() + ":page:1";
            stringRedisTemplate.delete(listCacheKey);
            if (comment.getRootId() != null && comment.getRootId() != 0) {
                String repliesCacheKey = COMMENT_REPLIES_KEY + comment.getRootId();
                stringRedisTemplate.delete(repliesCacheKey);
            }

            if ("CREATE".equals(notification.getType())) {
                handleCommentCreate(notification);
            } else if ("REPLY".equals(notification.getType())) {
                handleCommentReply(notification);
            }

            log.info("评论处理完成: commentId={}", comment.getId());

        } catch (Exception e) {
            log.error("消息处理失败 - 消息: {}, 错误: {}", message, e.getMessage(), e);
        }
    }

    private void handleCommentCreate(CommentNotification notification) {
        log.info("[通知] 新评论发布! 用户ID {} 在景点 {} 发布了评论",
                notification.getUserId(), notification.getAttractionId());
        log.info("[统计] 更新景点 {} 的评论数", notification.getAttractionId());
        String content = notification.getContent();
        log.info("[AI] 分析评论情感: {}",
                content != null && content.length() > 20 ? content.substring(0, 20) + "..." : content);
    }

    private void handleCommentReply(CommentNotification notification) {
        String content = notification.getContent();
        log.info("[通知] 评论 {} 收到回复! 回复内容: {}",
                notification.getParentId(),
                content != null && content.length() > 20 ? content.substring(0, 20) + "..." : content);
        log.info("[统计] 更新根评论 {} 的回复数", notification.getParentId());
    }

    public void triggerConsume() {
        listenQueue();
    }

    /**
     * 递归查找真正的顶级评论ID
     * 如果 parentId 对应的评论是顶级评论（parentId=0），则返回其自身ID
     * 否则继续向上查找
     */
    private Long findRootCommentId(Long commentId) {
        if (commentId == null || commentId <= 0) {
            return 0L;
        }
        Comment c = getById(commentId);
        if (c == null) {
            return 0L;
        }
        // 如果 parentId = 0，说明这是顶级评论，它自己的ID就是rootId
        if (c.getParentId() == null || c.getParentId() == 0) {
            return c.getId();
        }
        // 否则递归查询父评论
        return findRootCommentId(c.getParentId());
    }

    private void addCommentToHotRank(Comment comment) {
        String hotKey = ATTRACTION_HOT_COMMENTS_KEY + comment.getAttractionId();
        double hotScore = calculateAdvancedHotScore(
                comment.getLikeCount(),
                comment.getReplyCount(),
                comment.getCreateTime());
        stringRedisTemplate.opsForZSet().add(hotKey, comment.getId().toString(), hotScore);
        stringRedisTemplate.opsForZSet().removeRange(hotKey, 0, -(HOT_COMMENTS_LIMIT + 1));
    }

    private void updateParentHotScore(Long rootId, Long attractionId, int realReplyCount) {
        Comment rootComment = getById(rootId);
        if (rootComment != null) {
            String hotKey = ATTRACTION_HOT_COMMENTS_KEY + attractionId;
            String countKey = COMMENT_LIKE_COUNT_KEY + rootId;
            String likeCountStr = stringRedisTemplate.opsForValue().get(countKey);
            int likeCount = likeCountStr != null ? Integer.parseInt(likeCountStr) : rootComment.getLikeCount();
            // ⭐ Bug修复：使用 Redis 中的真实回复数（已 +1）
            double hotScore = calculateAdvancedHotScore(likeCount, realReplyCount, rootComment.getCreateTime());
            if (hotScore > 0) {
                stringRedisTemplate.opsForZSet().add(hotKey, rootId.toString(), hotScore);
            }
        }
    }

    private double calculateAdvancedHotScore(Integer likeCount, Integer replyCount, LocalDateTime createTime) {
        double baseScore = likeCount * 4.0 + replyCount * 3.0;
        long hoursSinceCreated = java.time.temporal.ChronoUnit.HOURS.between(
                createTime,
                LocalDateTime.now());
        double decayFactor = Math.log10(hoursSinceCreated + 10) + 1;
        return baseScore / decayFactor;
    }
}