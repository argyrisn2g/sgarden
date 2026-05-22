package com.sgarden.dto;

import lombok.Data;

@Data
public class OrderItemRequest {
    private String productId;
    private Integer quantity;
}
