package org.example.travel_commend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 订单实体类（MVP 精简版）
 * 存储门票/酒店预订订单信息
 */
@Data
@TableName("orders")
public class Orders implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 订单唯一ID（主键，自增）
     */
    @TableId(type = IdType.AUTO)
    private Long id;

    /**
     * 订单编号（业务单号，唯一）
     * 格式示例：20260106000001
     */
    private String orderNo;

    /**
     * 下单用户ID
     */
    private Long userId;

    /**
     * 景点ID（关联的景点）
     */
    private Long attractionId;

    /**
     * 产品类型
     * TICKET: 门票
     * HOTEL: 酒店
     * PACKAGE: 套票
     */
    private String productType;

    /**
     * 产品名称（如：成人票、儿童票、豪华房等）
     */
    private String productName;

    /**
     * 订单金额（单位：元）
     */
    private BigDecimal amount;

    /**
     * 购买数量
     */
    private Integer quantity;

    /**
     * 联系人姓名
     */
    private String contactName;

    /**
     * 联系人电话（用于接收订单通知）
     */
    private String contactPhone;

    /**
     * 计划游玩日期
     */
    private LocalDate visitDate;

    /**
     * 订单状态
     * PENDING: 待支付（刚创建订单）
     * PAID: 已支付（等待使用）
     * USED: 已使用（已核销/已入住）
     * CANCELLED: 已取消（用户取消或超时未支付）
     */
    private String status;

    /**
     * 支付时间
     */
    private LocalDateTime payTime;

    /**
     * 支付方式
     * ALIPAY: 支付宝
     * WECHAT: 微信支付
     * BANK: 银行卡
     */
    private String payMethod;

    /**
     * 订单创建时间
     */
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /**
     * 订单更新时间
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /**
     * 逻辑删除标志
     * 0: 未删除
     * 1: 已删除
     */
    @TableLogic
    private Integer deleted;
}
