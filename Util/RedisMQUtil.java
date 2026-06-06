package org.example.travel_commend.Util;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

/**
 * Redis消息队列工具类
 * 使用Redis List实现简单的消息队列
 */
@Component
@RequiredArgsConstructor
public class RedisMQUtil {

    private final StringRedisTemplate stringRedisTemplate;

    /**
     * 评论通知队列键
     */
    public static final String COMMENT_NOTIFY_QUEUE = "mq:comment:notify";

    /**
     * 发送消息到队列（生产者）
     * @param queueKey 队列键
     * @param message 消息内容
     */
    public void sendMessage(String queueKey, String message) {
        stringRedisTemplate.opsForList().leftPush(queueKey, message);
    }

    /**
     * 从队列接收消息（消费者）- 阻塞方式
     * @param queueKey 队列键
     * @param timeout 阻塞超时时间（秒）
     * @return 消息内容，超时返回null
     */
    public String receiveMessage(String queueKey, long timeout) {
        return stringRedisTemplate.opsForList().rightPop(queueKey, timeout, TimeUnit.SECONDS);
    }

    /**
     * 从队列接收消息（消费者）- 非阻塞方式
     * @param queueKey 队列键
     * @return 消息内容，队列为空返回null
     */
    public String receiveMessageNonBlocking(String queueKey) {
        return stringRedisTemplate.opsForList().rightPop(queueKey);
    }

    /**
     * 获取队列长度
     * @param queueKey 队列键
     * @return 队列中的消息数量
     */
    public long getQueueSize(String queueKey) {
        return stringRedisTemplate.opsForList().size(queueKey);
    }
}
