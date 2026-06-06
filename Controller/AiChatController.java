package org.example.travel_commend.Controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.ServletOutputStream;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.example.travel_commend.Service.UserService;
import org.example.travel_commend.Util.UserHolder;
import org.example.travel_commend.entity.User;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.LinkedHashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api")
@Tag(name = "AI 旅行助手", description = "AI 旅行规划对话接口")
public class AiChatController {

    @Value("${agent.python.url:http://localhost:8000}")
    private String agentUrl;

    private final UserService userService;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiChatController(UserService userService) {
        this.userService = userService;
        //RestTemplate是java用来发送请求给python的类
        SimpleClientHttpRequestFactory syncFactory = new SimpleClientHttpRequestFactory();
        //设置连接超时时间
        syncFactory.setConnectTimeout(5000);
        //设置读取超时时间
        syncFactory.setReadTimeout(300_000);
        this.restTemplate = new RestTemplate(syncFactory);

    }

    @PostMapping("/chat")
    @Operation(summary = "AI 对话（非流式）", description = "向 AI 旅行助手发送消息，返回完整结果")
    public Object chat(@RequestBody Map<String, Object> body) {
        //将用户的信息打包传给python
        enrichWithUserProfile(body);
        log.info("AI 对话：{}", body.get("query"));
        //调用8000端口的python服务将用户数据以及用户问的问题发送给python的agent，并获取agent返回的结果
        String json = restTemplate.postForObject(agentUrl + "/api/chat", body, String.class);
        try {
            //获取json数据
            return objectMapper.readValue(json, Map.class);
        } catch (Exception e) {
            log.error("解析 Python 响应失败", e);
            return Map.of("code", 500, "message", "AI 服务响应异常");
        }
    }

    @PostMapping(value = "/chat/stream", produces = "text/event-stream")
    @Operation(summary = "AI 对话（流式）", description = "向 AI 旅行助手发送消息，返回 SSE 流式结果")
    public void chatStream(@RequestBody Map<String, Object> body, HttpServletResponse response) throws Exception {
        enrichWithUserProfile(body);
        log.info("AI 流式对话：{}", body.get("query"));

        response.setContentType("text/event-stream");
        response.setCharacterEncoding("UTF-8");
        response.setHeader("Cache-Control", "no-cache");
        response.setHeader("Connection", "keep-alive");
        response.setBufferSize(0);

        HttpURLConnection conn = null;
        try {
            URL url = new URL(agentUrl + "/api/chat/stream");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            conn.setReadTimeout(300000);
            conn.setConnectTimeout(5000);

            try (OutputStream os = conn.getOutputStream()) {
                os.write(objectMapper.writeValueAsBytes(body));
                os.flush();
            }

            // 核心：逐行读取并立即转发
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                 ServletOutputStream os = response.getOutputStream()) {
                String line;
                while ((line = reader.readLine()) != null) {
                    os.write((line + "\n").getBytes());
                    os.flush(); // 每读一行就推给浏览器
                    // ⭐ 新增：检测客户端是否已断开

                }
            }
        }catch (IOException e) {
            if (e.getMessage().contains("Broken pipe") || e.getMessage().contains("Connection reset")) {
                log.info("检测到前端已断开连接，停止转发");
            } else {
                log.error("AI 流式对话失败", e);
                if (!response.isCommitted()) {
                    try {
                        response.setContentType("application/json;charset=utf-8");
                        response.getWriter().write("{\"code\":500,\"message\":\"AI 服务不可用\"}");
                    } catch (Exception ignored) {}
                }
            }
        } catch (Exception e) {
            log.error("AI 流式对话异常", e);
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    private void enrichWithUserProfile(Map<String, Object> body) {
        //获取用户信息
        Long userId = UserHolder.getUserId();
        if (userId == null) return;
        //存储用户信息
        body.put("user_id", String.valueOf(userId));

        try {
            User user = userService.getById(userId);
            if (user != null) {
                Map<String, Object> profile = new LinkedHashMap<>();
                profile.put("nickname", user.getNickname() != null ? user.getNickname() : "");
                profile.put("level", user.getLevel() != null ? user.getLevel() : 1);
                profile.put("bio", user.getBio() != null ? user.getBio() : "");
                body.put("user_profile", profile);
                log.info("注入用户画像: userId={}, nickname={}, level={}", userId, user.getNickname(), user.getLevel());
            }
        } catch (Exception e) {
            log.warn("查询用户画像失败, userId={}: {}", userId, e.getMessage());
        }
    }

    @PostMapping("/images/search")
    @Operation(summary = "搜索景点图片", description = "根据关键词搜索 Unsplash 图片")
    public Object searchImages(@RequestBody Map<String, Object> body) {
        String json = restTemplate.postForObject(agentUrl + "/api/images/search", body, String.class);
        try {
            return objectMapper.readValue(json, Map.class);
        } catch (Exception e) {
            return Map.of("code", 500, "message", "图片搜索失败");
        }
    }
}
