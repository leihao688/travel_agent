package org.example.travel_commend;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@MapperScan("org.example.travel_commend.Mapper")
@SpringBootApplication
@EnableScheduling
public class TravelCommendApplication {

    public static void main(String[] args) {
        SpringApplication.run(TravelCommendApplication.class, args);
    }

}
