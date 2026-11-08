package com.itsoumya.settlementguard.web;

import com.itsoumya.settlementguard.dto.ReconciliationRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRunResponse;
import com.itsoumya.settlementguard.service.ReconciliationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/reconciliation")
public class ReconciliationController {

    private final ReconciliationService reconciliation;

    public ReconciliationController(ReconciliationService reconciliation) {
        this.reconciliation = reconciliation;
    }

    @PostMapping("/runs")
    @ResponseStatus(HttpStatus.CREATED)
    public ReconciliationRunResponse run(@Valid @RequestBody ReconciliationRequest request) {
        return reconciliation.run(request);
    }

    @GetMapping("/runs/{id}")
    public ReconciliationRunResponse get(@PathVariable String id) {
        return reconciliation.get(id);
    }
}
