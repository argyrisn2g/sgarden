package com.sgarden.controller;

import com.sgarden.dto.ErrorResponse;
import com.sgarden.dto.PagedResponse;
import com.sgarden.dto.ProductRequest;
import com.sgarden.dto.ProductStatsResponse;
import com.sgarden.model.Product;
import com.sgarden.service.ProductService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    private static final Set<String> VALID_CATEGORIES =
            Set.of("Electronics", "Accessories", "Storage", "Networking");

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    private Map<String, String> validateProduct(ProductRequest request, boolean isCreate) {
        Map<String, String> errors = new LinkedHashMap<>();
        if (isCreate && (request.getName() == null || request.getName().isBlank())) {
            errors.put("name", "name is required");
        } else if (request.getName() != null && request.getName().isBlank()) {
            errors.put("name", "name cannot be empty");
        }
        if (request.getPrice() != null && request.getPrice() <= 0) {
            errors.put("price", "price must be a positive number");
        }
        if (request.getCategory() != null && !VALID_CATEGORIES.contains(request.getCategory())) {
            errors.put("category", "category must be one of: " +
                    VALID_CATEGORIES.stream().sorted().collect(Collectors.joining(", ")));
        }
        return errors;
    }

    @GetMapping
    public ResponseEntity<PagedResponse<Product>> getAllProducts(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int limit,
            @RequestParam(required = false) String sort,
            @RequestParam(defaultValue = "asc") String order) {
        return ResponseEntity.ok(productService.getAllProducts(page, limit, sort, order));
    }

    @GetMapping("/stats")
    public ResponseEntity<ProductStatsResponse> getProductStats() {
        return ResponseEntity.ok(productService.getProductStats());
    }

    @GetMapping("/search")
    public ResponseEntity<List<Product>> searchProducts(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) Double minPrice,
            @RequestParam(required = false) Double maxPrice) {
        return ResponseEntity.ok(productService.searchProducts(q, category, minPrice, maxPrice));
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> getProductById(@PathVariable String id) {
        return productService.getProductById(id)
                .map(product -> ResponseEntity.ok((Object) product))
                .orElse(ResponseEntity.status(HttpStatus.NOT_FOUND)
                        .body(new ErrorResponse("Product not found")));
    }

    @PostMapping
    public ResponseEntity<?> createProduct(@RequestBody ProductRequest request) {
        Map<String, String> errors = validateProduct(request, true);
        if (!errors.isEmpty()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(new ErrorResponse("Validation failed", errors));
        }
        Product product = productService.createProduct(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(product);
    }

    @PutMapping("/{id}")
    public ResponseEntity<?> updateProduct(@PathVariable String id,
                                           @RequestBody ProductRequest request) {
        Map<String, String> errors = validateProduct(request, false);
        if (!errors.isEmpty()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(new ErrorResponse("Validation failed", errors));
        }
        return productService.updateProduct(id, request)
                .map(product -> ResponseEntity.ok((Object) product))
                .orElse(ResponseEntity.status(HttpStatus.NOT_FOUND)
                        .body(new ErrorResponse("Product not found")));
    }

    @PatchMapping("/{id}/stock")
    public ResponseEntity<?> updateStock(@PathVariable String id,
                                         @RequestBody Map<String, Object> body) {
        Object raw = body.get("stock");
        if (raw == null || !(raw instanceof Number) || raw instanceof Boolean
                || ((Number) raw).doubleValue() < 0) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(new ErrorResponse("stock must be a non-negative number"));
        }
        int stock = ((Number) raw).intValue();
        return productService.updateStock(id, stock)
                .map(product -> ResponseEntity.ok((Object) product))
                .orElse(ResponseEntity.status(HttpStatus.NOT_FOUND)
                        .body(new ErrorResponse("Product not found")));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteProduct(@PathVariable String id) {
        if (productService.deleteProduct(id)) {
            return ResponseEntity.ok().build();
        }
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(new ErrorResponse("Product not found"));
    }
}
