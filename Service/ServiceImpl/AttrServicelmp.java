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
import org.example.travel_commend.Mapper.AttractionMapper;
import org.example.travel_commend.Mapper.UserMapper;
import org.example.travel_commend.Service.AttractionService;
import org.example.travel_commend.Service.UserService;
import org.example.travel_commend.Util.CaCheClient;
import org.example.travel_commend.Util.MultiLevelCacheClient;
import org.example.travel_commend.VO.AttractionVO;
import org.example.travel_commend.dto.AttractionDTO;
import org.example.travel_commend.dto.AttractionQueryDTO;
import org.example.travel_commend.dto.Result;
import org.example.travel_commend.entity.Attraction;
import org.example.travel_commend.entity.User;
import org.example.travel_commend.exception.BusinessException;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

import static org.example.travel_commend.Util.RedisConstants.*;

@Slf4j
@RequiredArgsConstructor
@Service
public class AttrServicelmp extends ServiceImpl<AttractionMapper, Attraction> implements AttractionService {
    private final StringRedisTemplate stringRedisTemplate;
    private final CaCheClient caCheClient;
    private final AttractionMapper attractionMapper;
    private final MultiLevelCacheClient multiLevelCache;
    /**
     * 缓存预热：项目启动完成后自动加载热门景点到缓存
     */
    @EventListener(ApplicationReadyEvent.class)
    public void warmUpHotAttractions() {
        log.info("🚀 开始缓存预热：加载热门景点数据");
        try {
            getHotAttractions();
            log.info("✅ 热门景点缓存预热完成");
        } catch (Exception e) {
            log.error("❌ 热门景点缓存预热失败", e);
        }
    }

    /**
     * 定时刷新：每 5 分钟自动刷新热门景点缓存
     */
    @Scheduled(fixedRate = 3000000) // 300000ms = 5 分钟
    public void scheduledRefreshHotAttractions() {
        log.info("⏰ 定时任务：刷新热门景点缓存");
        try {
            // 先清除旧缓存
            multiLevelCache.invalidate("attraction:hot");
            // 重新加载
            getHotAttractions();
            log.info("✅ 热门景点缓存定时刷新完成");
        } catch (Exception e) {
            log.error("❌ 热门景点缓存定时刷新失败", e);
        }
    }


    @Override
    @Transactional
    public Result<Void> createAttraction(AttractionDTO attractionDTO) {
        Attraction attraction = BeanUtil.copyProperties(attractionDTO, Attraction.class);

        attraction.setRating(BigDecimal.ZERO);
        attraction.setRatingCount(0);
        attraction.setCommentCount(0);
        attraction.setViewCount(0);
        attraction.setFavoriteCount(0);
        attraction.setStatus(1);

        save(attraction);
        log.info("创建景点成功 - 景点ID: {}, 名称: {}", attraction.getId(), attraction.getName());
        return Result.success();
    }
    @Transactional
    @Override
    public Result<Void> updateAttraction(Long id, AttractionDTO attractionDTO) {
        Attraction existingAttraction = getById(id);
        if (existingAttraction == null) {
            return Result.error("景点不存在");
        }
        BeanUtil.copyProperties(attractionDTO, existingAttraction,true);
        // 3. 执行更新
        boolean updated = updateById(existingAttraction);
        if (!updated) {
            return Result.error("更新景点信息失败");
        }

        // 4. 清除缓存
        stringRedisTemplate.delete(ATTRACTION_CACHE_KEY + id);
        log.info("更新景点成功并清除缓存 - 景点ID: {}", id);
        return Result.success();
    }

    @Override
    public Result<Void> deleteAttraction(Long id) {
        // 检查景点是否存在（MyBatis-Plus会自动过滤已删除的数据）
        Attraction attraction = getById(id);
        if (attraction == null) {
            return Result.error("景点不存在");
        }

        // 使用MyBatis-Plus的逻辑删除（自动设置deleted=1）
        removeById(id);

        // 清除缓存
        stringRedisTemplate.delete(ATTRACTION_CACHE_KEY + id);
        log.info("逻辑删除景点成功 - 景点ID: {}", id);
        return Result.success();
    }

    @Override
    public void increaseViewCount(Long id) {
        lambdaUpdate()
                .eq(Attraction::getId,id)
                .setSql("view_count=view_count+1")
                .update();
        }



    @Override
    public Result<AttractionVO> getAttractionById(Long id) {

         Attraction attraction =caCheClient.queryWithMutex(
                 ATTRACTION_CACHE_KEY,           // 缓存key前缀
                 LOCK_ATTRACTION_KEY,            // 锁key前缀
                 Attraction.class,             // 返回类型
                 id,                             // 景点ID
                 this::getById,        // ← 查询数据库的方法
                 ATTRACTION_CACHE_TTL);// 缓存过期时间
         AttractionVO attractionVO = new AttractionVO();
         BeanUtil.copyProperties(attraction, attractionVO);
         if (attraction == null){
             return Result.error("景点不存在");
         }
        // ⭐ 手动处理 images 字段的类型转换 (String -> List<String>)
        if (StrUtil.isNotBlank(attraction.getImages())) {
            try {
                attractionVO.setImages(JSONUtil.toList(attraction.getImages(), String.class));
            } catch (Exception e) {
                // 兼容非标准 JSON 格式（如逗号分隔的字符串）
                attractionVO.setImages(java.util.Arrays.asList(attraction.getImages().split(",")));
            }
        } else {
            attractionVO.setImages(new java.util.ArrayList<>());
        }

        return Result.success(attractionVO);

    }

    @Override public Result<Page<AttractionVO>> queryAttractions(AttractionQueryDTO queryDTO) {
        LambdaQueryWrapper<Attraction> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Attraction::getDeleted, 0)
                .eq(Attraction::getStatus, 1);

        // 2. 关键词查询（注意：必须加 and() 包裹，否则 OR 会导致 SQL 逻辑错误）
        /*
          @and(condition, lambda)：第一个参数 StrUtil.isNotBlank(...) 是开关。如果用户没搜关键词，这一整块代码直接跳过不执行。

         */
        wrapper.and(StrUtil.isNotBlank(queryDTO.getKeyword()), w ->
                w.like(Attraction::getName, queryDTO.getKeyword())
                        .or()
                        .like(Attraction::getDescription, queryDTO.getKeyword())
        );

        // 3. 其他条件（用 condition 参数替代 if，更简洁）
        wrapper.eq(StrUtil.isNotBlank(queryDTO.getCategory()), Attraction::getCategory, queryDTO.getCategory())
                .eq(StrUtil.isNotBlank(queryDTO.getSubCategory()), Attraction::getSubCategory, queryDTO.getSubCategory())
                .eq(StrUtil.isNotBlank(queryDTO.getProvince()), Attraction::getProvince, queryDTO.getProvince())
                .eq(StrUtil.isNotBlank(queryDTO.getCity()), Attraction::getCity, queryDTO.getCity())
                .ge(queryDTO.getMinPrice() != null, Attraction::getPrice, queryDTO.getMinPrice())
                .le(queryDTO.getMaxPrice() != null, Attraction::getPrice, queryDTO.getMaxPrice());

        // 4. 排序
        buildSortCondition(wrapper, queryDTO.getSortBy());

        // 5. 分页 + 转换 VO（用 convert 一行搞定）
        IPage<Attraction> page = new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize());
        IPage<AttractionVO> voPage = this.page(page, wrapper)
                .convert(attr -> {
                    AttractionVO vo = BeanUtil.copyProperties(attr, AttractionVO.class);
                    // 将 JSON 字符串解析为 List
                    if (cn.hutool.core.util.StrUtil.isNotBlank(attr.getImages())) {
                        vo.setImages(cn.hutool.json.JSONUtil.toList(attr.getImages(), String.class));
                    } else {
                        vo.setImages(new java.util.ArrayList<>());
                    }
                    return vo;
                });
                  return Result.success((Page<AttractionVO>) voPage);}

    @Override
    public Result<List<AttractionVO>> getHotAttractions() {
        List<AttractionVO> hotList = multiLevelCache.queryMultiLevel(
                "attraction:hot",
                (Class<List<AttractionVO>>) (Class<?>) List.class, // 1. 类型强转
                key -> {
                    // 2. 直接在 orderByDesc 中写 SQL 表达式
                    List<Attraction> list = lambdaQuery()
                            .last("ORDER BY (rating - 3) * LOG10(rating_count + 1) DESC limit 10")
                            .list();

                    // 3. 使用 copyToList 进行集合转换
                    return BeanUtil.copyToList(list, AttractionVO.class);
                },
                300
        );
        return Result.success(hotList);
    }
    @Override
    public Result<AttractionVO> getAttractionDetail(Long id) {
        AttractionVO detail = multiLevelCache.queryMultiLevel(
                "attraction:detail:" + id,
                AttractionVO.class,
                key -> {
                    Attraction attraction = getById(id);
                    return attraction == null ? null : BeanUtil.copyProperties(attraction, AttractionVO.class);
                },
                300 // 详情缓存 5 分钟
        );

        return Result.success(detail);
    }



    private void buildSortCondition(LambdaQueryWrapper<Attraction> wrapper, String sortBy) {
        if (StrUtil.isBlank(sortBy)) {
            wrapper.orderByDesc(Attraction::getCreateTime);
            return;
        }
        switch (sortBy) {
            case "rating" -> wrapper.orderByDesc(Attraction::getRating);
            case "price" -> wrapper.orderByAsc(Attraction::getPrice);
            case "viewCount" -> wrapper.orderByDesc(Attraction::getViewCount);
            default -> wrapper.orderByDesc(Attraction::getCreateTime);
        }
    }
    private double calculateHotScore(Double rating, Integer ratingCount) {
        if (rating == null || ratingCount == null || ratingCount == 0) {
            return 0.0;
        }
        // 基准分设为 3.0，低于 3 分热度为负
        double baseScore = rating - 3.0;
        // 人数对数衰减
        double weight = Math.log10(ratingCount + 1);
        return baseScore * weight * 100; // 乘以 100 方便排序和展示
    }


}
