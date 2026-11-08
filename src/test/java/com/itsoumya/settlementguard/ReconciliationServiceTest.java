package com.itsoumya.settlementguard;

import com.itsoumya.settlementguard.domain.BreakType;
import com.itsoumya.settlementguard.domain.PaymentEventType;
import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRow;
import com.itsoumya.settlementguard.service.PaymentEventService;
import com.itsoumya.settlementguard.service.ReconciliationService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class ReconciliationServiceTest {

    @Autowired
    private PaymentEventService events;

    @Autowired
    private ReconciliationService reconciliation;

    @Test
    void matchedSettlementIsReportedAsMatched() {
        events.ingest(request("TERM-001", "111111", "RRN-101", PaymentEventType.AUTHORIZATION, 10_000));
        events.ingest(request("TERM-001", "111111", "RRN-101", PaymentEventType.SETTLEMENT, 10_000));

        var run = reconciliation.run(request("RRN-101", 10_000));

        assertThat(run.matched()).isEqualTo(1);
        assertThat(run.breaks()).extracting("breakType").containsExactly("MATCHED");
    }

    @Test
    void missingAuthorizationIsExplicit() {
        var run = reconciliation.run(request("RRN-102", 10_000));

        assertThat(run.missingAuthorization()).isEqualTo(1);
        assertThat(run.breaks().get(0).breakType()).isEqualTo(BreakType.MISSING_AUTHORIZATION.name());
    }

    @Test
    void duplicateSettlementIsExplicit() {
        events.ingest(request("TERM-001", "111111", "RRN-103", PaymentEventType.AUTHORIZATION, 10_000));
        events.ingest(request("TERM-001", "111111", "RRN-103", PaymentEventType.SETTLEMENT, 10_000));
        events.ingest(request("TERM-002", "222222", "RRN-103", PaymentEventType.SETTLEMENT, 10_000));

        var run = reconciliation.run(request("RRN-103", 10_000));

        assertThat(run.duplicateSettlements()).isEqualTo(1);
        assertThat(run.breaks().get(0).breakType()).isEqualTo(BreakType.DUPLICATE_SETTLEMENT.name());
    }

    @Test
    void amountMismatchIsExplicit() {
        events.ingest(request("TERM-001", "111111", "RRN-104", PaymentEventType.AUTHORIZATION, 10_000));
        events.ingest(request("TERM-001", "111111", "RRN-104", PaymentEventType.SETTLEMENT, 9_000));

        var run = reconciliation.run(request("RRN-104", 10_000));

        assertThat(run.amountMismatches()).isEqualTo(1);
        assertThat(run.breaks().get(0).breakType()).isEqualTo(BreakType.AMOUNT_MISMATCH.name());
        assertThat(run.breaks().get(0).expectedCents()).isEqualTo(10_000);
        assertThat(run.breaks().get(0).actualCents()).isEqualTo(9_000);
    }

    @Test
    void authorizationWithoutSettlementIsDelayed() {
        events.ingest(request("TERM-001", "111111", "RRN-105", PaymentEventType.AUTHORIZATION, 10_000));

        var run = reconciliation.run(request("RRN-105", 10_000));

        assertThat(run.delayedSettlements()).isEqualTo(1);
        assertThat(run.breaks().get(0).breakType()).isEqualTo(BreakType.DELAYED_SETTLEMENT.name());
    }

    private ReconciliationRequest request(String rrn, long amountCents) {
        return new ReconciliationRequest("settlement-2026-11-04.csv", List.of(
                new ReconciliationRow(rrn, amountCents, "NZD", Instant.parse("2026-11-04T02:00:00Z"), "TERM-001", "111111")
        ));
    }

    private IngestPaymentEventRequest request(
            String terminal,
            String stan,
            String rrn,
            PaymentEventType type,
            long amountCents
    ) {
        return new IngestPaymentEventRequest(
                terminal,
                stan,
                rrn,
                type,
                amountCents,
                "NZD",
                Instant.parse("2026-11-04T00:00:00Z"),
                1,
                type + ":" + rrn + ":" + amountCents + ":" + terminal
        );
    }
}
