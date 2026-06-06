package org.example.travel_commend.Util;

public class RedisConstants {
    public static final String CODE_KEY_PREFIX = "user:code:";
    public static final long CODE_EXPIRE_MINUTES = 5;
    public static final String LOGIN_USER_KEY = "login:token:";
    public static final Long LOGIN_USER_TTL = 30L;

    public static final String ATTRACTION_CACHE_KEY = "attraction:detail:";
    public static final Long ATTRACTION_CACHE_TTL = 30L;
    public static final Long CACHE_NULL_TTL = 2L;
    public static final String LOCK_ATTRACTION_KEY = "lock:attraction:";
    public static final Long LOCK_ATTRACTION_TTL = 10L;
    public static final String ATTRACTION_HOT_KEY = "attraction:hot:";
    public static final Long ATTRACTION_HOT_TTL = 10L;

    // 热门评论排行榜 ZSet key
    public static final String ATTRACTION_HOT_COMMENTS_KEY = "attraction:hot_comments:";
    // 最多缓存前 200 条热门评论
    public static final Long HOT_COMMENTS_LIMIT = 200L;

    public static final String COMMENT_FIRST_PAGE = ":page:1";

    // 评论列表和回复缓存（按时间排序时使用）
    public static final String COMMENT_LIST_KEY = "comment:list:";
    public static final Long COMMENT_LIST_TTL = 10L;
    public static final String COMMENT_REPLIES_KEY = "comment:replies:";
    public static final Long COMMENT_REPLIES_TTL = 10L;

    public static final String COMMENT_LIKE_KEY = "comment:like:";
    public static final String COMMENT_LIKE_COUNT_KEY = "comment:likeCount:";
    public static final String COMMENT_LIKE_LOCK_KEY = "lock:comment:like:";
    public static final Long COMMENT_LIKE_LOCK_TTL = 5L;
    public static final String COMMENT_LIKE_SYNC_SET = "comment:like:sync_set";
    public static final String SIGN_KEY_PREFIX = "sign:user:";
    // 实时回复数 key（与 MySQL 异步同步）
    public static final String COMMENT_REPLY_COUNT_KEY = "comment:replyCount:";
}
