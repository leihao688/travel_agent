package org.example.travel_commend.Config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

@Configuration
public class SyncConfig {
    @Bean("likeSyncExecutor")
    public ThreadPoolExecutor likeSyncExecutor() {
        return new ThreadPoolExecutor(
                2,
                5,
                60L,
                TimeUnit.SECONDS,
                new ArrayBlockingQueue<>(500),
                new ThreadPoolExecutor.CallerRunsPolicy()
        );
    }
}

