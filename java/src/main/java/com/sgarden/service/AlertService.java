package com.sgarden.service;

import com.sgarden.model.AppSetting;
import com.sgarden.model.Product;
import com.sgarden.repository.ProductRepository;
import com.sgarden.repository.SettingsRepository;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class AlertService {

    private static final String THRESHOLD_KEY = "alert_threshold";
    private static final int DEFAULT_THRESHOLD = 10;

    private final SettingsRepository settingsRepository;
    private final MongoTemplate mongoTemplate;

    public AlertService(SettingsRepository settingsRepository, MongoTemplate mongoTemplate) {
        this.settingsRepository = settingsRepository;
        this.mongoTemplate = mongoTemplate;
    }

    public int getThreshold() {
        return settingsRepository.findByKey(THRESHOLD_KEY)
                .map(s -> ((Number) s.getValue()).intValue())
                .orElse(DEFAULT_THRESHOLD);
    }

    public int setThreshold(int threshold) {
        AppSetting setting = settingsRepository.findByKey(THRESHOLD_KEY)
                .orElse(new AppSetting(null, THRESHOLD_KEY, threshold));
        setting.setValue(threshold);
        settingsRepository.save(setting);
        return threshold;
    }

    public List<Map<String, Object>> getAlerts() {
        int threshold = getThreshold();
        Query query = new Query(Criteria.where("stock").lt(threshold));
        List<Product> lowStock = mongoTemplate.find(query, Product.class);

        List<Map<String, Object>> alerts = new ArrayList<>();
        for (Product p : lowStock) {
            int stock = p.getStock() != null ? p.getStock() : 0;
            Map<String, Object> alert = new LinkedHashMap<>();
            alert.put("productId", p.getId());
            alert.put("name", p.getName());
            alert.put("stock", stock);
            alert.put("threshold", threshold);
            alert.put("severity", severity(stock, threshold));
            alerts.add(alert);
        }
        return alerts;
    }

    private String severity(int stock, int threshold) {
        if (stock <= threshold * 0.33) return "critical";
        if (stock <= threshold * 0.66) return "warning";
        return "info";
    }
}
