package org.example.travel_commend.Service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

/**
 * Redis消息队列服务
 * 基于Redis List实现生产者-消费者模式
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class MessageQueueService {

    private final StringRedisTemplate stringRedisTemplate;

    /**
     * 评论通知队列Key
     */
    public static final String COMMENT_NOTIFICATION_QUEUE = "queue:comment:notification";

    /**
     * 发送消息到队列（生产者）
     * @param queueKey 队列名称
     * @param message 消息内容
     */
    public void sendMessage(String queueKey, String message) {
        stringRedisTemplate.opsForList().leftPush(queueKey, message);
        log.info("消息发送成功 - 队列: {}, 消息: {}", queueKey, message);
    }

    /**
     * 从队列接收消息（消费者）
     * 使用阻塞方式，队列为空时阻塞等待
     * @param queueKey 队列名称
     * @return 消息内容
     */
    public String receiveMessage(String queueKey) {
        // 使用 BRPOP 阻塞式弹出，超时时间30秒
        // BRPOP: 阻塞式弹出列表最后一个元素
        var result = stringRedisTemplate.opsForList().rightPop(queueKey, 30, java.util.concurrent.TimeUnit.SECONDS);
        if (result != null) {
            log.info("消息接收成功 - 队列: {}, 消息: {}", queueKey, result);
        }
        return result;
    }

    /**
     * 非阻塞方式接收消息
     * @param queueKey 队列名称
     * @return 消息内容，如果队列为空返回null
     */
    public String receiveMessageNonBlocking(String queueKey) {
        return stringRedisTemplate.opsForList().rightPop(queueKey);
    }

    /**
     * 获取队列长度
     * @param queueKey 队列名称
     * @return 队列中消息数量
     */
    public Long getQueueSize(String queueKey) {
        return stringRedisTemplate.opsForList().size(queueKey);
    }
}