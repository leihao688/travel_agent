package org.example.travel_commend.Util;

import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONUtil;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import java.util.function.Function;
import java.time.LocalDateTime;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
@Slf4j
@Component
public class MultiLevelCacheClient {
    @Resource
    private StringRedisTemplate stringRedisTemplate;
    // 用于存储当前线程获取锁时的唯一凭证（防止误删）
    private static final ThreadLocal<String> lockValueHolder = new ThreadLocal<>();

    //L1缓存：Caffeine本地缓存（最大1000条，5分钟无访问过期）
    private final Cache<String, Object> localCache = Caffeine.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(5, TimeUnit.MINUTES)
            .expireAfterAccess(2, TimeUnit.MINUTES)
            .recordStats()
            .build();
    // 异步重建缓存线程池
    private static final ExecutorService CACHE_REBUILD_EXECUTOR = new ThreadPoolExecutor(
            5, //核心线程数
            10,//最大线程数
            60L,//最大存活时间
            TimeUnit.SECONDS,
            new ArrayBlockingQueue<>(100),
            new ThreadPoolExecutor.CallerRunsPolicy()
    );
    /**
     * 多级缓存查询
     * L1: Caffeine → L2: Redis → L3: MySQL
     */
    @SuppressWarnings("unchecked")
    public <R> R queryMultiLevel(String key, Class<R> type, Function<String, R> dbFallback, long redisTTL) {

        // L1: 查询Caffeine本地缓存
        Object l1Result = localCache.getIfPresent(key);
        if (l1Result != null) {
            log.debug("L1缓存命中: {}", key);
            return (R) l1Result;
        }

        // L2: 查询Redis缓存
        String redisKey = "cache:multi:" + key;
        String redisJson = stringRedisTemplate.opsForValue().get(redisKey);
        if (StrUtil.isNotBlank(redisJson)) {
            String trimmedJson = redisJson.trim();
            boolean isValidJson = trimmedJson.startsWith("{") || trimmedJson.startsWith("[");

            if (isValidJson) {
                // 2. 格式正确，正常解析
                R result;
                if (JSONUtil.isTypeJSONArray(redisJson)) {
                    result = (R) JSONUtil.parseArray(redisJson);
                } else {
                    result = JSONUtil.toBean(redisJson, type);
                }

                localCache.put(key, result);
                log.debug("L2 缓存命中: {}", key);
                return result;
            } else {
                // 3. 格式错误（脏数据），删除它
                log.warn("检测到 Redis 脏数据，已自动清除: {}", key);
                stringRedisTemplate.delete(redisKey);
            }
        }

        R dbResult;
        String lockKey = "lock:" + key;

        // 尝试获取分布式锁
        boolean lock = tryLockWithRetry(lockKey, 3, 10);
        if (lock) {
            try {
                // 双重检查：拿到锁后，再看一眼缓存是不是已经被别的线程建好了
                String doubleCheckJson = stringRedisTemplate.opsForValue().get(redisKey);
                if (StrUtil.isNotBlank(doubleCheckJson) && (doubleCheckJson.trim().startsWith("{") || doubleCheckJson.trim().startsWith("["))) {
                    dbResult = JSONUtil.isTypeJSONArray(doubleCheckJson) ? (R) JSONUtil.parseArray(doubleCheckJson) : JSONUtil.toBean(doubleCheckJson, type);
                    localCache.put(key, dbResult);
                    return dbResult;
                }

                // 确认没有缓存，才去查数据库
                dbResult = dbFallback.apply(key);

                if (dbResult != null) {
                    stringRedisTemplate.opsForValue().set(redisKey, JSONUtil.toJsonStr(dbResult), redisTTL, TimeUnit.SECONDS);
                    localCache.put(key, dbResult);
                } else {
                    // 数据库也没数据，缓存空值防穿透
                    stringRedisTemplate.opsForValue().set(redisKey, "", 1, TimeUnit.MINUTES);
                }
            } finally {
                unlock(lockKey);
            }
        } else {
            // 没拿到锁，说明有别的线程正在重建缓存，我们稍微等一下再读
            try { Thread.sleep(50); } catch (InterruptedException e) { e.printStackTrace(); }
            String retryJson = stringRedisTemplate.opsForValue().get(redisKey);
            if (StrUtil.isNotBlank(retryJson) && (retryJson.trim().startsWith("{") || retryJson.trim().startsWith("["))) {
                dbResult = JSONUtil.isTypeJSONArray(retryJson) ? (R) JSONUtil.parseArray(retryJson) : JSONUtil.toBean(retryJson, type);
                localCache.put(key, dbResult);
                return dbResult;
            }
            // 如果等了还没好，只能降级去查库（保证可用性）
            dbResult = dbFallback.apply(key);
        }

        return dbResult;
    }

    private boolean tryLockWithRetry(String key, long waitSeconds, long leaseSeconds) {
        String uuid = java.util.UUID.randomUUID().toString();
        long endTime = System.currentTimeMillis() + waitSeconds * 1000;
        while (System.currentTimeMillis() < endTime) {
            // 存 UUID 而不是 "1"，这样每个线程的锁都有独一无二的身份证
            Boolean flag = stringRedisTemplate.opsForValue().setIfAbsent(key, uuid, leaseSeconds, TimeUnit.SECONDS);
            if (Boolean.TRUE.equals(flag)) {
                lockValueHolder.set(uuid); // 记录凭证
                return true;
            }
            try { Thread.sleep(50); } catch (InterruptedException e) { return false; }
        }
        return false;
    }


    /**
     * 带逻辑过期的查询（适用于热点数据）
     */
    @SuppressWarnings("unchecked")
    public <R> R queryWithLogicalExpire(String key, Class<R> type, Function<String, R> dbFallback, long logicalExpireSeconds) {

        // L1缓存查询
        Object l1Result = localCache.getIfPresent(key);
        if (l1Result != null) {
            return (R) l1Result;
        }

        // L2缓存查询
        String redisKey = "cache:logical:" + key;
        String redisJson = stringRedisTemplate.opsForValue().get(redisKey);

        if (StrUtil.isBlank(redisJson)) {
            return rebuildCacheWithLock(key, type, dbFallback, logicalExpireSeconds);
        }

        RedisData redisData = JSONUtil.toBean(redisJson, RedisData.class);
        R result = JSONUtil.toBean(JSONUtil.toJsonStr(redisData.getData()), type);

        // 判断是否逻辑过期
        if (redisData.getExpireTime().isAfter(LocalDateTime.now())) {
            localCache.put(key, result);
            return result;
        }

        // 已过期，异步重建
        String lockKey = "lock:logical:" + key;
        boolean lock = tryLock(lockKey);
        if (lock) {
            CACHE_REBUILD_EXECUTOR.submit(() -> {
                try {
                    rebuildCacheWithLock(key, type, dbFallback, logicalExpireSeconds);
                } finally {
                    unlock(lockKey);
                }
            });
        }

        localCache.put(key, result);
        return result;
    }
    /**
     * 带锁的缓存重建
     */
    private <R> R rebuildCacheWithLock(String key, Class<R> type, Function<String, R> dbFallback, long logicalExpireSeconds) {
        String redisKey = "cache:logical:" + key;

        R dbResult = dbFallback.apply(key);
        if (dbResult == null) {
            stringRedisTemplate.opsForValue().set(redisKey, "", 1, TimeUnit.MINUTES);
            return null;
        }

        RedisData redisData = new RedisData();
        redisData.setData(dbResult);
        redisData.setExpireTime(LocalDateTime.now().plusSeconds(logicalExpireSeconds));

        stringRedisTemplate.opsForValue().set(redisKey, JSONUtil.toJsonStr(redisData));
        localCache.put(key, dbResult);

        log.info("缓存重建完成: {}", key);
        return dbResult;
    }

    /**
     * 清除多级缓存
     */
    public void invalidate(String key) {
        localCache.invalidate(key);
        stringRedisTemplate.delete("cache:multi:" + key);
        stringRedisTemplate.delete("cache:logical:" + key);
        log.info("多级缓存已清除: {}", key);
    }

    /**
     * 获取缓存统计
     */
    public String getCacheStats() {
        var stats = localCache.stats();
        return String.format("命中率: %.2f%%, 命中: %d, 未命中: %d, 当前大小: %d",
                stats.hitRate() * 100, stats.hitCount(), stats.missCount(),
                localCache.estimatedSize());
    }

    private boolean tryLock(String key) {
        Boolean flag = stringRedisTemplate.opsForValue().setIfAbsent(key, "1", 10, TimeUnit.SECONDS);
        return Boolean.TRUE.equals(flag);
    }

    private void unlock(String key) {
        String uuid = lockValueHolder.get();
        if (uuid == null) return; // 如果没有凭证，说明没锁或者已经解过了

        // 使用 Lua 脚本保证“判断”和“删除”的原子性
        String script = "if redis.call('get', KEYS[1]) == ARGV[1] then " +
                "    return redis.call('del', KEYS[1]) " +
                "else " +
                "    return 0 " +
                "end";

        try {
            stringRedisTemplate.execute(
                    new org.springframework.data.redis.core.script.DefaultRedisScript<>(script, Long.class),
                    java.util.Collections.singletonList(key),
                    uuid
            );
        } finally {
            lockValueHolder.remove(); // 清理 ThreadLocal，防止内存泄漏
        }
    }
}


