package org.example.travel_commend.Service.ServiceImpl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Mapper.AttrCommentMapper;
import org.example.travel_commend.Service.AttCommentService;
import org.example.travel_commend.Service.AttractionService;
import org.example.travel_commend.Service.CommentNotificationConsumer;
import org.example.travel_commend.Service.LevelService;
import org.example.travel_commend.Service.LikeRecordService;
import org.example.travel_commend.Service.MessageQueueService;
import org.example.travel_commend.Service.UserService;
import org.example.travel_commend.Util.MultiLevelCacheClient;
import org.example.travel_commend.Util.RedisConstants;
import org.example.travel_commend.Util.UserHolder;
import org.example.travel_commend.VO.CommentVO;
import org.example.travel_commend.dto.CommentDTO;
import org.example.travel_commend.dto.CommentQueryDTO;
import org.example.travel_commend.dto.Result;
import org.example.travel_commend.entity.Comment;
import org.example.travel_commend.entity.User;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import static org.example.travel_commend.Util.RedisConstants.*;

@Service
@Slf4j
@RequiredArgsConstructor
public class ACommentServiceImp extends ServiceImpl<AttrCommentMapper, Comment> implements AttCommentService {

    private final AttractionService attractionService;
    private final UserService userService;
    private final LikeRecordService likeRecordService;
    private final StringRedisTemplate stringRedisTemplate;
    private final MessageQueueService messageQueueService;
    private final LevelService levelService;

    @Override
    public Result<Void> createComment(CommentDTO commentDTO) {
        Long userId = UserHolder.getUserId();
        if (userId == null)
            return Result.error("用户未登录");

        Comment comment = BeanUtil.copyProperties(commentDTO, Comment.class);
        comment.setUserId(userId);
        Long parentId = comment.getParentId();
        boolean isTopLevel = (parentId == null || parentId == 0);

        if (isTopLevel) {
            Long attractionId = commentDTO.getAttractionId();
            if (attractionId == null || attractionId <= 0)
                return Result.error("景点ID无效");
            if (attractionService.getById(attractionId) == null)
                return Result.error("景点不存在");
            if (commentDTO.getRating() == null)
                return Result.error("主评论必须填写评分");
            comment.setParentId(0L);
        } else {
            Comment parent = getById(parentId);
            if (parent == null)
                return Result.error("父评论不存在");
            comment.setAttractionId(parent.getAttractionId());
            comment.setRating(null);
            comment.setRootId(parent.getRootId());
        }

        CommentNotificationConsumer.CommentNotification notification = new CommentNotificationConsumer.CommentNotification();
        notification.setCommentId(null);
        notification.setUserId(userId);
        notification.setAttractionId(comment.getAttractionId());
        notification.setContent(comment.getContent());
        notification.setRating(comment.getRating());
        notification.setParentId(parentId);
        notification.setType(isTopLevel ? "CREATE" : "REPLY");

        messageQueueService.sendMessage(
                MessageQueueService.COMMENT_NOTIFICATION_QUEUE,
                JSONUtil.toJsonStr(notification));

        return Result.success();
    }

    @Override
    public Result<Page<CommentVO>> getAttractionComments(CommentQueryDTO queryDTO) {
        if ("likeCount".equals(queryDTO.getSortBy())) {
            return getHotComments(queryDTO);
        }
        return getCommentsByTime(queryDTO);
    }

    private Result<Page<CommentVO>> getHotComments(CommentQueryDTO queryDTO) {
        String hotKey = ATTRACTION_HOT_COMMENTS_KEY + queryDTO.getAttractionId();
        // ⭐ 从 Redis 获取总数量
        Long total = stringRedisTemplate.opsForZSet().zCard(hotKey);
        if (total == null || total == 0) {
            log.info("ZSet为空，初始化热门排行榜：{}", hotKey);
            initHotRankFromDB(queryDTO.getAttractionId());
            total = stringRedisTemplate.opsForZSet().zCard(hotKey);
            if (total == null || total == 0) {
                return getCommentsByTime(queryDTO);
            }
        }
        // ⭐ Bug修复：total 应该以 MySQL 中的真实评论数为准
        // 因为 ZSet 可能与 MySQL 不一致（新评论未加入、已删除评论未清理等）
        Long dbTotal = lambdaQuery()
                .eq(Comment::getAttractionId, queryDTO.getAttractionId())
                .eq(Comment::getParentId, 0)
                .eq(Comment::getStatus, 1)
                .count();
        total = dbTotal != null ? dbTotal : total;
        // 获取分页的起始索引
        long start = ((long) queryDTO.getPageNum() - 1) * queryDTO.getPageSize();
        // 获取分页的结束索引
        long end = start + queryDTO.getPageSize() - 1;
        // 使用zset来存储=成员 + 分数，分数重高向下排序
        Set<String> hotCommentIds = stringRedisTemplate.opsForZSet()
                .reverseRange(hotKey, start, end);

        if (hotCommentIds == null || hotCommentIds.isEmpty()) {
            return getCommentsByTime(queryDTO);
        }
        // 将set的数据转化为List，保持ZSet的倒序顺序
        List<Long> commentIds = hotCommentIds.stream().map(Long::parseLong).toList();
        // 用 Map 保持 ZSet 的顺序：分数越高的ID，order越小
        Map<Long, Integer> orderMap = new HashMap<>();
        for (int i = 0; i < commentIds.size(); i++) {
            orderMap.put(commentIds.get(i), i);
        }
        // 批量查询评论解决n+1问题
        List<Comment> comments = lambdaQuery()
                .in(Comment::getId, commentIds)
                .eq(Comment::getStatus, 1)
                .list()
                .stream()
                .sorted(Comparator.comparingInt(c -> orderMap.getOrDefault(c.getId(), Integer.MAX_VALUE)))
                .toList();

        Page<CommentVO> voPage = buildVOPageWithTotal(comments, queryDTO, commentIds, total);
        return Result.success(voPage);
    }

    private Page<CommentVO> buildVOPageWithTotal(List<Comment> comments,
            CommentQueryDTO queryDTO,
            List<Long> commentIds, Long total) {
        // 批量查询用户信息，去掉相同用户发不同评论的情况
        List<Long> userIds = comments.stream().map(Comment::getUserId).distinct().toList();
        // 将用户信息转化为Map，key为userId，value为User对象
        Map<Long, User> userMap = userService.listByIds(userIds).stream()
                .collect(Collectors.toMap(User::getId, u -> u));
        if (!userIds.isEmpty()) {
            userMap = userService.listByIds(userIds).stream()
                    .collect(Collectors.toMap(User::getId, u -> u));
        }
        Long currentUserId = UserHolder.getUserId();
        // 判断当前用户是否有登录，如果有登录则获取当前用户点赞的评论
        Set<Long> likedIds = (currentUserId != null && !commentIds.isEmpty())
                ? likeRecordService.getUserLikedComments(currentUserId, new ArrayList<>(commentIds))
                : new HashSet<>();

        Page<CommentVO> voPage = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        voPage.setTotal(total);
        // 将用户名和用户头像设置到VO对象中
        Map<Long, User> finalUserMap = userMap;
        voPage.setRecords(comments.stream().map(c -> {
            CommentVO vo = BeanUtil.copyProperties(c, CommentVO.class);
            User user = finalUserMap.get(c.getUserId());
            if (user != null) {
                vo.setUserName(user.getNickname());
                vo.setUserAvatar(user.getAvatar());
            }
            vo.setIsLiked(likedIds.contains(c.getId()));
            // ⭐ Bug修复：用 Redis 中的实时回复数覆盖 MySQL 的旧数据
            String redisReplyCount = stringRedisTemplate.opsForValue().get(COMMENT_REPLY_COUNT_KEY + c.getId());
            if (redisReplyCount != null) {
                vo.setReplyCount(Integer.parseInt(redisReplyCount));
            }
            return vo;
        }).toList());
        return voPage;
    }

    private Result<Page<CommentVO>> getCommentsByTime(CommentQueryDTO queryDTO) {
        String cacheKey = COMMENT_LIST_KEY + queryDTO.getAttractionId() + ":page:" + queryDTO.getPageNum();

        if (queryDTO.getPageNum() == 1) {
            String cacheJson = stringRedisTemplate.opsForValue().get(cacheKey);
            if (StrUtil.isNotBlank(cacheJson)) {
                Page<CommentVO> cachedPage = JSONUtil.toBean(cacheJson, Page.class);
                // ⭐ Bug修复：缓存命中时也用 Redis 实时覆盖 replyCount
                if (cachedPage != null && cachedPage.getRecords() != null) {
                    cachedPage.getRecords().forEach(vo -> {
                        String redisCount = stringRedisTemplate.opsForValue()
                                .get(COMMENT_REPLY_COUNT_KEY + vo.getId());
                        if (redisCount != null) {
                            vo.setReplyCount(Integer.parseInt(redisCount));
                        }
                    });
                }
                return Result.success(cachedPage);
            }
        }

        LambdaQueryWrapper<Comment> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Comment::getAttractionId, queryDTO.getAttractionId())
                .eq(Comment::getParentId, 0)
                .eq(Comment::getStatus, 1)
                .orderByDesc(Comment::getCreateTime);

        Page<Comment> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        Page<Comment> commentPage = this.page(page, wrapper);

        Page<CommentVO> resultPage = buildVOPage(commentPage.getRecords(), queryDTO,
                commentPage.getRecords().stream().map(Comment::getId).collect(Collectors.toSet()));

        if (queryDTO.getPageNum() == 1) {
            stringRedisTemplate.opsForValue().set(cacheKey, JSONUtil.toJsonStr(resultPage), COMMENT_LIST_TTL,
                    TimeUnit.MINUTES);
        }
        return Result.success(resultPage);
    }

    private Page<CommentVO> buildVOPage(List<Comment> comments, CommentQueryDTO queryDTO, Collection<Long> commentIds) {
        List<Long> userIds = comments.stream().map(Comment::getUserId).distinct().toList();
        Map<Long, User> userMap = new HashMap<>();
        // ⭐ 增加非空判断：避免生成 "id IN ()" 导致 SQL 语法错误
        if (!userIds.isEmpty()) {
            userMap = userService.listByIds(userIds).stream()
                    .collect(Collectors.toMap(User::getId, u -> u));
        }
        Long currentUserId = UserHolder.getUserId();
        Set<Long> likedIds = (currentUserId != null && !commentIds.isEmpty())
                ? likeRecordService.getUserLikedComments(currentUserId, new ArrayList<>(commentIds))
                : new HashSet<>();

        Page<CommentVO> voPage = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        Map<Long, User> finalUserMap = userMap;
        voPage.setRecords(comments.stream().map(c -> {
            CommentVO vo = BeanUtil.copyProperties(c, CommentVO.class);
            User user = finalUserMap.get(c.getUserId());
            if (user != null) {
                vo.setUserName(user.getNickname());
                vo.setUserAvatar(user.getAvatar());
            }
            vo.setIsLiked(likedIds.contains(c.getId()));
            // ⭐ Bug修复：用 Redis 中的实时回复数覆盖 MySQL 的旧数据
            String redisReplyCount = stringRedisTemplate.opsForValue().get(COMMENT_REPLY_COUNT_KEY + c.getId());
            if (redisReplyCount != null) {
                vo.setReplyCount(Integer.parseInt(redisReplyCount));
            }
            return vo;
        }).toList());
        return voPage;
    }

    public void addCommentToHotRank(Comment comment) {
        String hotKey = ATTRACTION_HOT_COMMENTS_KEY + comment.getAttractionId();

        // ⭐ 使用高级算法计算热门度分数
        double hotScore = calculateAdvancedHotScore(
                comment.getLikeCount(),
                comment.getReplyCount(),
                comment.getCreateTime());

        stringRedisTemplate.opsForZSet().add(hotKey, comment.getId().toString(), hotScore);
        stringRedisTemplate.opsForZSet().removeRange(hotKey, 0, -(HOT_COMMENTS_LIMIT + 1));
    }

    /**
     * 从数据库初始化热门排行榜（ZSet 为空时调用）
     */
    public void initHotRankFromDB(Long attractionId) {
        String hotKey = ATTRACTION_HOT_COMMENTS_KEY + attractionId;

        // 查询该景点下所有正常的顶级评论
        List<Comment> comments = lambdaQuery()
                .eq(Comment::getAttractionId, attractionId)
                .eq(Comment::getParentId, 0)
                .eq(Comment::getStatus, 1)
                .orderByDesc(Comment::getLikeCount)
                .last("LIMIT " + HOT_COMMENTS_LIMIT)
                .list();

        if (comments.isEmpty()) {
            return;
        }

        // 批量加入 ZSet
        Set<ZSetOperations.TypedTuple<String>> tuples = comments.stream()
                .map(c -> ZSetOperations.TypedTuple.of(
                        c.getId().toString(),
                        calculateAdvancedHotScore(c.getLikeCount(), c.getReplyCount(), c.getCreateTime())))
                .collect(Collectors.toSet());

        stringRedisTemplate.opsForZSet().add(hotKey, tuples);
        log.info("初始化景点 {} 的热门排行榜，共 {} 条", attractionId, comments.size());
    }

    /**
     * 高级热门度算法（Reddit风格）
     * 
     * @param likeCount  点赞数
     * @param replyCount 回复数
     * @param createTime 创建时间
     * @return 热门度分数
     */
    private double calculateAdvancedHotScore(Integer likeCount, Integer replyCount, LocalDateTime createTime) {
        // 1. 基础互动分数：点赞×4 + 回复×3
        double baseScore = likeCount * 4.0 + replyCount * 3.0;

        // 2. 时间衰减：使用对数函数，但调整系数使其更温和
        long hoursSinceCreated = java.time.temporal.ChronoUnit.HOURS.between(
                createTime,
                LocalDateTime.now());

        // ⭐ 优化方案1：使用更大的底数（以10为底）
        // log10(1) = 0, log10(24) = 1.38, log10(720) = 2.86
        double decayFactor = Math.log10(hoursSinceCreated + 10) + 1;

        // 或者 ⭐ 优化方案2：自然对数 + 系数调整
        // ln(e) = 1, ln(24+e) = 3.25, ln(720+e) = 6.58
        // double decayFactor = Math.log(hoursSinceCreated + Math.E);

        // 3. 最终分数
        return baseScore / decayFactor;

    }

    public void updateParentHotScore(Long rootId, Long attractionId) {
        Comment rootComment = getById(rootId);
        if (rootComment != null) {
            String hotKey = ATTRACTION_HOT_COMMENTS_KEY + attractionId;

            // 从 Redis 获取最新点赞数
            String countKey = COMMENT_LIKE_COUNT_KEY + rootId;
            String likeCountStr = stringRedisTemplate.opsForValue().get(countKey);
            int likeCount = likeCountStr != null ? Integer.parseInt(likeCountStr) : rootComment.getLikeCount();

            // 回复数需要+1（因为刚发布了一条回复）
            int replyCount = rootComment.getReplyCount() + 1;

            double hotScore = calculateAdvancedHotScore(likeCount, replyCount, rootComment.getCreateTime());
            stringRedisTemplate.opsForZSet().add(hotKey, rootId.toString(), hotScore);
        }
    }

    @Override
    public Result<Page<CommentVO>> getCommentReplies(CommentQueryDTO queryDTO) {
        Long rootCommentId = queryDTO.getId();
        if (rootCommentId == null || rootCommentId <= 0)
            return Result.error("根评论ID无效");

        LambdaQueryWrapper<Comment> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Comment::getRootId, rootCommentId)
                .ne(Comment::getParentId, 0)
                .eq(Comment::getStatus, 1)
                .orderByAsc(Comment::getCreateTime);

        IPage<Comment> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        Page<Comment> commentPage = (Page<Comment>) this.page(page, wrapper);

        List<Long> userIds = commentPage.getRecords().stream()
                .map(Comment::getUserId)
                .distinct()
                .toList();
        Map<Long, User> userMap;
        if (!userIds.isEmpty()) {
            userMap = userService.listByIds(userIds).stream()
                    .collect(Collectors.toMap(User::getId, u -> u));
        } else {
            userMap = new HashMap<>();
        }
        List<Long> commentIds = commentPage.getRecords().stream()
                .map(Comment::getId)
                .toList();
        Long currentUserId = UserHolder.getUserId();
        Set<Long> likedIds = (currentUserId != null && !commentIds.isEmpty())
                ? likeRecordService.getUserLikedComments(currentUserId, commentIds)
                : new HashSet<>();

        Page<CommentVO> voPage = new Page<>(commentPage.getCurrent(), commentPage.getSize(), commentPage.getTotal());
        voPage.setRecords(commentPage.getRecords().stream().map(c -> {
            CommentVO vo = BeanUtil.copyProperties(c, CommentVO.class);
            User user = userMap.get(c.getUserId());
            if (user != null) {
                vo.setUserName(user.getNickname());
                vo.setUserAvatar(user.getAvatar());
            }
            vo.setIsLiked(likedIds.contains(c.getId()));
            return vo;
        }).toList());

        // ⭐ Bug修复：用 Redis 中的实时回复数覆盖 MySQL 的旧数据
        String redisReplyCount = stringRedisTemplate.opsForValue().get(COMMENT_REPLY_COUNT_KEY + rootCommentId);
        if (redisReplyCount != null) {
            voPage.setTotal(Long.parseLong(redisReplyCount));
        }

        return Result.success(voPage);
    }

    /**
     * 发送评论通知到消息队列
     * 
     * @param comment  评论实体
     * @param parentId 父评论ID（null表示顶级评论）
     */
    private void sendCommentNotification(Comment comment, Long parentId) {
        // 判断是新评论还是回复评论
        String type = (parentId == null || parentId == 0) ? "CREATE" : "REPLY";

        // 构建通知消息（使用普通POJO的setter方式）
        CommentNotificationConsumer.CommentNotification notification = new CommentNotificationConsumer.CommentNotification();
        notification.setCommentId(comment.getId());
        notification.setUserId(comment.getUserId());
        notification.setAttractionId(comment.getAttractionId());
        notification.setContent(comment.getContent());
        notification.setParentId(parentId);
        notification.setType(type);

        // 发送到消息队列
        messageQueueService.sendMessage(
                MessageQueueService.COMMENT_NOTIFICATION_QUEUE,
                JSONUtil.toJsonStr(notification));

        // 添加经验值奖励
        if ("CREATE".equals(type)) {
            // 发布评论获得经验
            levelService.addExp(comment.getUserId(), LevelService.ExpType.COMMENT.getExp(),
                    LevelService.ExpType.COMMENT);
        } else {
            // 发布回复获得经验
            levelService.addExp(comment.getUserId(), LevelService.ExpType.REPLY.getExp(), LevelService.ExpType.REPLY);
        }
    }
}
