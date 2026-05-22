package com.sgarden.service;

import com.sgarden.dto.SalesAnalyticsResponse;
import com.sgarden.model.Order;
import com.sgarden.model.OrderItem;
import com.sgarden.model.Product;
import com.sgarden.repository.OrderRepository;
import com.sgarden.repository.ProductRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class AnalyticsService {

    private static final DateTimeFormatter PERIOD_FMT =
            DateTimeFormatter.ofPattern("yyyy-MM").withZone(ZoneOffset.UTC);

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;

    public AnalyticsService(OrderRepository orderRepository, ProductRepository productRepository) {
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
    }

    public SalesAnalyticsResponse getSalesAnalytics(Instant startDate, Instant endDate) {
        List<Order> orders = orderRepository.findAll().stream()
                .filter(o -> {
                    Instant created = o.getCreatedAt();
                    if (created == null) return false;
                    if (startDate != null && created.isBefore(startDate)) return false;
                    if (endDate != null && created.isAfter(endDate)) return false;
                    return true;
                })
                .collect(Collectors.toList());

        if (orders.isEmpty()) {
            return new SalesAnalyticsResponse(0, 0, List.of(), List.of());
        }

        double totalRevenue = Math.round(
                orders.stream().mapToDouble(o -> o.getTotal() != null ? o.getTotal() : 0).sum() * 100.0) / 100.0;
        long totalOrders = orders.size();

        // Aggregate quantities per product
        Map<String, Integer> productQty = new LinkedHashMap<>();
        for (Order order : orders) {
            if (order.getItems() == null) continue;
            for (OrderItem item : order.getItems()) {
                productQty.merge(item.getProductId(), item.getQuantity(), Integer::sum);
            }
        }

        // Build top products sorted by quantity desc, top 10
        List<SalesAnalyticsResponse.TopProduct> topProducts = productQty.entrySet().stream()
                .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
                .limit(10)
                .map(e -> {
                    Optional<Product> p = productRepository.findById(e.getKey());
                    String name = p.map(Product::getName).orElse(e.getKey());
                    double price = p.map(prod -> prod.getPrice() != null ? prod.getPrice() : 0.0).orElse(0.0);
                    double rev = Math.round(e.getValue() * price * 100.0) / 100.0;
                    return new SalesAnalyticsResponse.TopProduct(e.getKey(), name, e.getValue(), rev);
                })
                .collect(Collectors.toList());

        // Revenue by period (YYYY-MM)
        Map<String, Double> periodRevenue = new TreeMap<>();
        for (Order order : orders) {
            if (order.getCreatedAt() == null) continue;
            String period = PERIOD_FMT.format(order.getCreatedAt());
            periodRevenue.merge(period, order.getTotal() != null ? order.getTotal() : 0.0, Double::sum);
        }

        List<SalesAnalyticsResponse.PeriodRevenue> revenueByPeriod = periodRevenue.entrySet().stream()
                .map(e -> new SalesAnalyticsResponse.PeriodRevenue(
                        e.getKey(), Math.round(e.getValue() * 100.0) / 100.0))
                .collect(Collectors.toList());

        return new SalesAnalyticsResponse(totalRevenue, totalOrders, topProducts, revenueByPeriod);
    }
}
