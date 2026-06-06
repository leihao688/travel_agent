package org.example.travel_commend.Service.ServiceImpl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import jakarta.annotation.Resource;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Mapper.AttrCommentMapper;
import org.example.travel_commend.Mapper.LikeRecordMapper;
import org.example.travel_commend.Service.LevelService;
import org.example.travel_commend.Service.LikeRecordService;
import org.example.travel_commend.Service.MessageQueueService;
import org.example.travel_commend.Util.RedisConstants;
import org.example.travel_commend.Util.UserHolder;
import org.example.travel_commend.dto.Result;
import org.example.travel_commend.entity.Comment;
import org.example.travel_commend.entity.LikeRecord;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import static org.example.travel_commend.Util.RedisConstants.*;

/**
 * 点赞业务实现类
 * 基于 Redis 实现高性能点赞功能
 */
@RequiredArgsConstructor
@Service
@Slf4j
public class LikeRecordServiceImp extends ServiceImpl<LikeRecordMapper, LikeRecord> implements LikeRecordService {
    private final StringRedisTemplate stringRedisTemplate;
    private final AttrCommentMapper attrCommentMapper;
    private final LevelService levelService;
    private final MessageQueueService messageQueueService;

    @Resource(name = "likeSyncExecutor")
    private ThreadPoolExecutor likeSyncExecutor;

    // 点赞统计队列（用于定时任务批量同步）
    private static final String LIKE_STAT_QUEUE = "queue:like:stat";
    // 点赞总数ZSet Key（业务类型 -> (bizId, count)）
    private static final String LIKE_COUNT_ZSET = "like:count:zset";

    /**
     * 点赞/取消点赞
     * 根据流程图实现：
     * 1. SADD bizId uid - 新增点赞记录
     * 2. 判断返回值：1=点赞成功，0=取消点赞
     * 3. SCARD bizId - 统计点赞数量
     * 4. ZADD key count bizId - 缓存点赞总数
     */
    @Override
    public Result<Void> toggleLike(Long commentId) {
        Long userId = UserHolder.getUserId();
        if (userId == null)
            return Result.error("用户未登录");

        String likeKey = COMMENT_LIKE_KEY + commentId;
        String countKey = COMMENT_LIKE_COUNT_KEY + commentId;
        String lockKey = COMMENT_LIKE_LOCK_KEY + commentId;
        String userIdStr = userId.toString();

        try {
            // 获取分布式锁，防止并发问题
            boolean lockAcquired = Boolean.TRUE.equals(
                    stringRedisTemplate.opsForValue().setIfAbsent(lockKey, "1", COMMENT_LIKE_LOCK_TTL,
                            TimeUnit.SECONDS));
            if (!lockAcquired)
                return Result.error("操作过于频繁");

            Comment comment = attrCommentMapper.selectById(commentId);
            if (comment == null)
                return Result.error("评论不存在");

            // ⭐ 流程图步骤1: SADD bizId uid - 新增点赞记录（原子操作）
            // 返回1表示新增成功（之前未点赞），返回0表示已存在（取消点赞）
            Long addResult = stringRedisTemplate.opsForSet().add(likeKey, userIdStr);

            boolean liked = addResult != null && addResult == 1;

            if (!liked) {
                // ⭐ 取消点赞：从集合中移除
                stringRedisTemplate.opsForSet().remove(likeKey, userIdStr);
                stringRedisTemplate.opsForValue().decrement(countKey);
                log.info("取消点赞成功 - commentId: {}, userId: {}", commentId, userId);
            } else {
                // ⭐ 点赞成功
                stringRedisTemplate.opsForValue().increment(countKey);

                // ⭐ 给评论作者添加经验值奖励（不能给自己点赞加经验）
                if (!userId.equals(comment.getUserId())) {
                    levelService.addExp(comment.getUserId(), LevelService.ExpType.COMMENT_LIKED.getExp(),
                            LevelService.ExpType.COMMENT_LIKED);
                }
                log.info("点赞成功 - commentId: {}, userId: {}", commentId, userId);
            }

            // ⭐ 流程图步骤3: SCARD bizId - 统计点赞数量
            Long likeCount = stringRedisTemplate.opsForSet().size(likeKey);

            // ⭐ 流程图步骤4: ZADD key count bizId - 缓存点赞总数到ZSet
            if (likeCount != null) {
                stringRedisTemplate.opsForZSet().add(LIKE_COUNT_ZSET, commentId.toString(), likeCount);
            }

            // 更新热门度分数
            updateCommentHotScore(comment, likeCount != null ? likeCount.intValue() : comment.getLikeCount());

            // 标记需要同步到数据库
            stringRedisTemplate.opsForSet().add(COMMENT_LIKE_SYNC_SET, commentId.toString());

            // 发送到统计队列（用于定时任务通知业务方）
            sendLikeStatToQueue(commentId, likeCount != null ? likeCount.intValue() : 0);

            return Result.success();
        } finally {
            stringRedisTemplate.delete(lockKey);
        }
    }

    /**
     * 发送点赞统计信息到消息队列
     */
    private void sendLikeStatToQueue(Long commentId, int count) {
        Map<String, Object> statMessage = new HashMap<>();
        statMessage.put("bizId", commentId);
        statMessage.put("bizType", "comment");
        statMessage.put("likeCount", count);
        statMessage.put("timestamp", System.currentTimeMillis());

        messageQueueService.sendMessage(LIKE_STAT_QUEUE,
                cn.hutool.json.JSONUtil.toJsonStr(statMessage));
    }

    /**
     * 更新评论热门度分数
     */
    private void updateCommentHotScore(Comment comment, int likeCount) {
        String hotKey = ATTRACTION_HOT_COMMENTS_KEY + comment.getAttractionId();

        // ⭐ Bug修复：优先用 Redis 中的实时回复数（不用 MySQL 脏数据）
        String replyCountKey = COMMENT_REPLY_COUNT_KEY + comment.getId();
        String replyCountStr = stringRedisTemplate.opsForValue().get(replyCountKey);
        int replyCount = replyCountStr != null ? Integer.parseInt(replyCountStr)
                : (comment.getReplyCount() == null ? 0 : comment.getReplyCount());

        // 使用高级算法计算分数
        double hotScore = calculateAdvancedHotScore(likeCount, replyCount, comment.getCreateTime());

        // ⭐ Bug修复：分数 <= 0 时删除 ZSet 成员（无效数据）
        if (hotScore <= 0) {
            stringRedisTemplate.opsForZSet().remove(hotKey, comment.getId().toString());
            return;
        }

        // 更新 ZSet 中的分数
        stringRedisTemplate.opsForZSet().add(hotKey, comment.getId().toString(), hotScore);
    }

    /**
     * 高级热门度分数算法
     */
    private double calculateAdvancedHotScore(int likeCount, int replyCount, LocalDateTime createTime) {
        // 1. 基础互动分数：点赞×4 + 回复×3
        double baseScore = likeCount * 4.0 + replyCount * 3.0;

        // 2. 时间衰减：使用对数函数
        long hoursSinceCreated = java.time.temporal.ChronoUnit.HOURS.between(
                createTime, LocalDateTime.now());

        // 使用以10为底的对数进行时间衰减
        double decayFactor = Math.log10(hoursSinceCreated + 10) + 1;

        // 3. 最终分数
        return baseScore / decayFactor;
    }

    @Override
    public boolean isLiked(Long userId, Long commentId) {
        return Boolean.TRUE
                .equals(stringRedisTemplate.opsForSet().isMember(COMMENT_LIKE_KEY + commentId, userId.toString()));
    }

    @Override
    public Set<Long> getUserLikedComments(Long userId, List<Long> commentIds) {
        return commentIds.stream().filter(id -> isLiked(userId, id)).collect(Collectors.toSet());
    }

    /**
     * 获取点赞数量（优先从Redis获取）
     */
    public int getLikeCount(Long commentId) {
        String countKey = COMMENT_LIKE_COUNT_KEY + commentId;
        String countStr = stringRedisTemplate.opsForValue().get(countKey);
        if (countStr != null) {
            return Integer.parseInt(countStr);
        }

        // 从数据库获取
        Comment comment = attrCommentMapper.selectById(commentId);
        return comment != null ? comment.getLikeCount() : 0;
    }

    /**
     * 定时任务：同步点赞数据到MySQL
     * 流程图中的定时任务部分：
     * 1. 选择某个业务类型
     * 2. 批量读取并移除 bizId 和点赞总数
     * 3. 通过MQ通知业务方
     */
    @Override
    @Scheduled(fixedRate = 10000)
    public void syncLikeDataToMySQL() {
        Set<String> dirtyIds = stringRedisTemplate.opsForSet().members(COMMENT_LIKE_SYNC_SET);
        if (dirtyIds == null || dirtyIds.isEmpty())
            return;

        likeSyncExecutor.submit(() -> {
            // 批量处理
            List<String> idList = new ArrayList<>(dirtyIds);

            for (String idStr : idList) {
                try {
                    Long commentId = Long.parseLong(idStr);
                    String likeKey = COMMENT_LIKE_KEY + commentId;
                    Set<String> userIds = stringRedisTemplate.opsForSet().members(likeKey);
                    int count = userIds != null ? userIds.size() : 0;

                    // 更新评论表的点赞数
                    Comment update = new Comment();
                    update.setId(commentId);
                    update.setLikeCount(count);
                    attrCommentMapper.updateById(update);

                    // 更新点赞记录表
                    lambdaUpdate().eq(LikeRecord::getCommentId, commentId).remove();
                    if (userIds != null && !userIds.isEmpty()) {
                        saveBatch(userIds.stream().map(uid -> {
                            LikeRecord r = new LikeRecord();
                            r.setUserId(Long.parseLong(uid));
                            r.setCommentId(commentId);
                            return r;
                        }).toList());
                    }

                    // 从同步集合中移除
                    stringRedisTemplate.opsForSet().remove(COMMENT_LIKE_SYNC_SET, idStr);

                    log.info("点赞数据同步成功 - commentId: {}, count: {}", commentId, count);
                } catch (Exception e) {
                    log.error("点赞数据同步失败 - commentId: {}", idStr, e);
                }
            }
        });
    }

    /**
     * 定时任务：处理点赞统计队列，通过MQ通知业务方
     * 每30秒执行一次
     */
    @Scheduled(fixedRate = 30000)
    public void processLikeStatQueue() {
        // 批量读取并移除队列中的消息
        List<String> messages = new ArrayList<>();
        String message;

        // 一次性读取最多100条消息
        for (int i = 0; i < 100; i++) {
            message = messageQueueService.receiveMessageNonBlocking(LIKE_STAT_QUEUE);
            if (message == null) {
                break;
            }
            messages.add(message);
        }

        if (!messages.isEmpty()) {
            log.info("处理点赞统计消息 - 数量: {}", messages.size());

            // 这里可以通过MQ通知其他业务方（如通知服务）
            // 目前我们已经在点赞时直接处理了经验值奖励
            // 可以扩展为通知评论作者等功能
        }
    }
}