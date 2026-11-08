package com.itsoumya.settlementguard.web;

import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import com.itsoumya.settlementguard.dto.PaymentEventResponse;
import com.itsoumya.settlementguard.service.PaymentEventService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/payments")
public class PaymentEventController {

    private final PaymentEventService payments;

    public PaymentEventController(PaymentEventService payments) {
        this.payments = payments;
    }

    @PostMapping("/events")
    public ResponseEntity<PaymentEventResponse> ingest(@Valid @RequestBody IngestPaymentEventRequest request) {
        PaymentEventResponse response = payments.ingest(request);
        HttpStatus status = "DUPLICATE".equals(response.status()) ? HttpStatus.OK : HttpStatus.CREATED;
        return ResponseEntity.status(status).body(response);
    }

    @GetMapping
    public List<PaymentEventResponse> recent(@RequestParam(defaultValue = "20") int limit) {
        return payments.recent(limit);
    }

    @GetMapping("/{rrn}")
    public List<PaymentEventResponse> byRrn(@PathVariable String rrn) {
        return payments.findByRrn(rrn);
    }
}
