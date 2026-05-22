package com.sgarden.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.util.List;

@Data
@AllArgsConstructor
public class SalesAnalyticsResponse {
    private double totalRevenue;
    private long totalOrders;
    private List<TopProduct> topProducts;
    private List<PeriodRevenue> revenueByPeriod;

    @Data
    @AllArgsConstructor
    public static class TopProduct {
        private String productId;
        private String name;
        private int totalQuantity;
        private double totalRevenue;
    }

    @Data
    @AllArgsConstructor
    public static class PeriodRevenue {
        private String period;
        private double revenue;
    }
}
