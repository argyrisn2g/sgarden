package com.sgarden.controller;

import com.sgarden.dto.ErrorResponse;
import com.sgarden.dto.SalesAnalyticsResponse;
import com.sgarden.service.AnalyticsService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;

@RestController
@RequestMapping("/api/analytics")
public class AnalyticsController {

    private final AnalyticsService analyticsService;

    public AnalyticsController(AnalyticsService analyticsService) {
        this.analyticsService = analyticsService;
    }

    @GetMapping("/sales")
    public ResponseEntity<?> getSalesAnalytics(
            @RequestParam(required = false) String startDate,
            @RequestParam(required = false) String endDate) {
        try {
            Instant start = startDate != null
                    ? LocalDate.parse(startDate).atStartOfDay(ZoneOffset.UTC).toInstant()
                    : null;
            Instant end = endDate != null
                    ? LocalDate.parse(endDate).atTime(23, 59, 59).toInstant(ZoneOffset.UTC)
                    : null;
            SalesAnalyticsResponse result = analyticsService.getSalesAnalytics(start, end);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(new ErrorResponse("Invalid date format. Use YYYY-MM-DD"));
        }
    }
}
