package com.itsoumya.settlementguard.web;

import com.itsoumya.settlementguard.dto.DashboardSummary;
import com.itsoumya.settlementguard.service.DashboardService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/dashboard")
public class DashboardController {

    private final DashboardService dashboard;

    public DashboardController(DashboardService dashboard) {
        this.dashboard = dashboard;
    }

    @GetMapping("/summary")
    public DashboardSummary summary() {
        return dashboard.summary();
    }
}
