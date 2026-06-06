package org.example.travel_commend.Util;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.ThreadPoolExecutor;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

import java.util.concurrent.TimeUnit;
import java.util.function.Function;

import static org.example.travel_commend.Util.RedisConstants.*;

@Slf4j
@Component
public class CaCheClient {
    @Resource
    private StringRedisTemplate stringRedisTemplate;
    private static final ExecutorService CACHE_REBUILD_EXECUTOR = new ThreadPoolExecutor(
            5,                    // 核心线程
            10,                   // 最大线程
            60L,                  // 空闲线程存活时间
            TimeUnit.SECONDS,
            new ArrayBlockingQueue<>(100),  // 有界队列（关键：防OOM）
            new ThreadPoolExecutor.CallerRunsPolicy() // 拒绝策略：安全不丢任务
    );
    public <R,ID> R queryWithLogic( String prefix,
                                    String keyPrefix,
                                    Class<R> type,
                                    ID id,
                                    Function<ID,R> dbFallback,
                                    Long expireSeconds) {
        String key= prefix+id;
        String objectJson = stringRedisTemplate.opsForValue().get(key);
        if(StrUtil.isBlank(objectJson)){
            return null;
        } //将redisData先转化为ObjectJson再进行反序列化
        RedisData redisData = JSONUtil.toBean(objectJson, RedisData.class);

        JSONObject objectJson2 = (JSONObject) redisData.getData();
        R r = JSONUtil.toBean(objectJson2, type);
        LocalDateTime expireTime = redisData.getExpireTime();
        if(expireTime.isAfter(LocalDateTime.now())){
            return r;
        }
        // 4. 尝试获取锁
        String lockKey = keyPrefix + key;
        boolean lock = tryLock(lockKey);
        if(lock){//拿到锁就找一个线程进行缓存重建
            CACHE_REBUILD_EXECUTOR.submit(()->{
                try {
                    saveShop2Redis(id,prefix,dbFallback, type, expireSeconds, TimeUnit.SECONDS);
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
                finally {
                    unlock(lockKey);
                }
            });
        }  objectJson = stringRedisTemplate.opsForValue().get(key);
        if(StrUtil.isBlank(objectJson)){
            return null;
        }
        redisData = JSONUtil.toBean(objectJson, RedisData.class);
        //将redisData先转化为ObjectJosn再进行反序列化
        objectJson2 = (JSONObject) redisData.getData();
        r = JSONUtil.toBean(objectJson2, type);
        return r;

    }
    public <R,ID> R queryWithMutex(
            String prefix,
            String keyPrefix,
            Class<R> type,
            ID id,
            Function<ID,R> dbFallback,
            Long cacheTTL
    ) {
        String key = prefix + id;

        // 1. 从 Redis 查询
        String json = stringRedisTemplate.opsForValue().get(key);

        // 2. 判断是否为空字符串（缓存空值）
        if (StrUtil.isNotBlank(json)) {
            // 空字符串说明是缓存的空值，直接返回 null
            if ("".equals(json)) {
                return null;
            }
            return JSONUtil.toBean(json, type);
        }

        // 3. 如果是 null（第一次查询）
        if (json != null) {
            return null;
        }

        // 4. 尝试获取锁
        String lockKey = keyPrefix + key;
        boolean lock = tryLock(lockKey);
        if (!lock) {
            // 获取锁失败，休眠后重试
            try {
                Thread.sleep(50);
                return queryWithMutex(prefix,keyPrefix, type, id, dbFallback, cacheTTL);
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
        }

        try {
            // 5. 获取锁成功，查询数据库
            R result = dbFallback.apply(id);

            // 6. 数据库查询结果为空，写入空字符串
            if (result == null) {
                stringRedisTemplate.opsForValue().set(key, "", CACHE_NULL_TTL, TimeUnit.MINUTES);
                return null;
            }

            // 7. 写入 Redis
            stringRedisTemplate.opsForValue().set(key, JSONUtil.toJsonStr(result), cacheTTL, TimeUnit.MINUTES);
            return result;

        } finally {
            unlock(lockKey);
        }
    }

    public boolean tryLock(String key){
        Boolean lock = stringRedisTemplate.opsForValue().setIfAbsent(key, "1", LOCK_ATTRACTION_TTL, TimeUnit.SECONDS);
        return Boolean.TRUE.equals(lock);

    }
    public void unlock(String key){
        stringRedisTemplate.delete(key);
    }
    private <R,ID> void saveShop2Redis(ID id, String prefix,Function<ID,R>dBFallBack, Class<R> type, Long expireSeconds,TimeUnit unit) {
        R r=dBFallBack.apply(id);
        RedisData redisData = new RedisData();
        redisData.setData(BeanUtil.beanToMap(r));
        redisData.setExpireTime(LocalDateTime.now().plusSeconds(unit.toSeconds(expireSeconds)));
        stringRedisTemplate.opsForValue().set(prefix+id,JSONUtil.toJsonStr(redisData));

    }
}
