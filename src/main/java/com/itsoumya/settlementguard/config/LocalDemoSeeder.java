package com.itsoumya.settlementguard.config;

import com.itsoumya.settlementguard.domain.PaymentEventType;
import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRow;
import com.itsoumya.settlementguard.service.PaymentEventService;
import com.itsoumya.settlementguard.service.ReconciliationService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;

@Component
@Profile("local")
public class LocalDemoSeeder implements CommandLineRunner {

    private final PaymentEventService payments;
    private final ReconciliationService reconciliation;

    public LocalDemoSeeder(PaymentEventService payments, ReconciliationService reconciliation) {
        this.payments = payments;
        this.reconciliation = reconciliation;
    }

    @Override
    public void run(String... args) {
        authorization("RRN-1001", 12_500);
        settlement("RRN-1001", 12_500, "TERM-001", "111111");
        authorization("RRN-1002", 8_800);
        settlement("RRN-1003", 5_500, "TERM-002", "222222");
        authorization("RRN-1004", 7_500);
        settlement("RRN-1004", 7_500, "TERM-001", "111111");
        settlement("RRN-1004", 7_500, "TERM-003", "333333");

        reconciliation.run(new ReconciliationRequest("demo-settlement-2026-11-04.csv", List.of(
                new ReconciliationRow("RRN-1001", 12_500, "NZD", Instant.parse("2026-11-04T02:00:00Z"), "TERM-001", "111111"),
                new ReconciliationRow("RRN-1002", 8_800, "NZD", Instant.parse("2026-11-04T02:00:00Z"), "TERM-001", "111111"),
                new ReconciliationRow("RRN-1003", 5_500, "NZD", Instant.parse("2026-11-04T02:00:00Z"), "TERM-002", "222222"),
                new ReconciliationRow("RRN-1004", 7_500, "NZD", Instant.parse("2026-11-04T02:00:00Z"), "TERM-001", "111111")
        )));
    }

    private void authorization(String rrn, long amount) {
        payments.ingest(request(rrn, PaymentEventType.AUTHORIZATION, amount, "TERM-001", "111111"));
    }

    private void settlement(String rrn, long amount, String terminal, String stan) {
        payments.ingest(request(rrn, PaymentEventType.SETTLEMENT, amount, terminal, stan));
    }

    private IngestPaymentEventRequest request(
            String rrn,
            PaymentEventType type,
            long amount,
            String terminal,
            String stan
    ) {
        return new IngestPaymentEventRequest(
                terminal,
                stan,
                rrn,
                type,
                amount,
                "NZD",
                Instant.parse("2026-11-04T00:00:00Z"),
                1,
                type + ":" + rrn + ":" + amount + ":" + terminal
        );
    }
}
