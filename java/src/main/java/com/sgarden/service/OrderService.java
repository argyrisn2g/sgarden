package com.sgarden.service;

import com.sgarden.dto.OrderRequest;
import com.sgarden.model.Order;
import com.sgarden.model.OrderItem;
import com.sgarden.model.Product;
import com.sgarden.repository.OrderRepository;
import com.sgarden.repository.ProductRepository;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class OrderService {

    private static final Map<String, List<String>> VALID_TRANSITIONS = new HashMap<>();

    static {
        VALID_TRANSITIONS.put("pending",   List.of("confirmed", "cancelled"));
        VALID_TRANSITIONS.put("confirmed", List.of("shipped"));
        VALID_TRANSITIONS.put("shipped",   List.of("delivered"));
        VALID_TRANSITIONS.put("delivered", List.of());
        VALID_TRANSITIONS.put("cancelled", List.of());
    }

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;

    public OrderService(OrderRepository orderRepository, ProductRepository productRepository) {
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
    }

    public Order createOrder(OrderRequest request) {
        List<OrderItem> items = request.getItems().stream()
                .map(i -> new OrderItem(i.getProductId(), i.getQuantity()))
                .collect(Collectors.toList());

        // Phase 1: validate stock for every item before any modification
        Map<String, Product> fetched = new HashMap<>();
        for (OrderItem item : items) {
            Product product = productRepository.findById(item.getProductId())
                    .orElseThrow(() -> new IllegalArgumentException("Product not found: " + item.getProductId()));
            int available = product.getStock() != null ? product.getStock() : 0;
            if (available < item.getQuantity()) {
                throw new IllegalArgumentException(
                        "Insufficient stock for '" + product.getName() + "'");
            }
            fetched.put(item.getProductId(), product);
        }

        // Phase 2: all checks passed — reduce stock and create order
        double total = 0.0;
        for (OrderItem item : items) {
            Product p = fetched.get(item.getProductId());
            total += (p.getPrice() != null ? p.getPrice() : 0.0) * item.getQuantity();
            p.setStock(p.getStock() - item.getQuantity());
            productRepository.save(p);
        }
        total = Math.round(total * 100.0) / 100.0;

        Order order = new Order();
        order.setStatus("pending");
        order.setItems(items);
        order.setTotal(total);
        return orderRepository.save(order);
    }

    public List<Order> getAllOrders(String status) {
        if (status != null && !status.isBlank()) {
            return orderRepository.findByStatus(status);
        }
        return orderRepository.findAll();
    }

    public Optional<Order> getOrderById(String id) {
        return orderRepository.findById(id);
    }

    public Optional<Order> updateOrder(String id, OrderRequest request) {
        return orderRepository.findById(id).map(order -> {
            List<OrderItem> items = request.getItems().stream()
                    .map(i -> new OrderItem(i.getProductId(), i.getQuantity()))
                    .collect(Collectors.toList());

            double total = items.stream()
                    .mapToDouble(item -> {
                        Optional<Product> p = productRepository.findById(item.getProductId());
                        double price = p.map(prod -> prod.getPrice() != null ? prod.getPrice() : 0.0).orElse(0.0);
                        return price * item.getQuantity();
                    })
                    .sum();
            total = Math.round(total * 100.0) / 100.0;

            order.setItems(items);
            order.setTotal(total);
            return orderRepository.save(order);
        });
    }

    public Optional<Order> updateOrderStatus(String id, String newStatus) {
        return orderRepository.findById(id).map(order -> {
            String current = order.getStatus() != null ? order.getStatus() : "pending";
            List<String> allowed = VALID_TRANSITIONS.getOrDefault(current, List.of());
            if (!allowed.contains(newStatus)) {
                throw new IllegalArgumentException(
                        "Cannot transition from '" + current + "' to '" + newStatus + "'");
            }
            order.setStatus(newStatus);
            return orderRepository.save(order);
        });
    }

    public boolean deleteOrder(String id) {
        if (orderRepository.existsById(id)) {
            orderRepository.deleteById(id);
            return true;
        }
        return false;
    }
}
