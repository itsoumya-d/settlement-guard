package com.itsoumya.settlementguard;

import com.itsoumya.settlementguard.audit.AuditChainService;
import com.itsoumya.settlementguard.domain.PaymentEventType;
import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import com.itsoumya.settlementguard.repository.AuditRecordRepository;
import com.itsoumya.settlementguard.service.PaymentEventService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class AuditChainTest {

    @Autowired
    private PaymentEventService payments;

    @Autowired
    private AuditChainService audit;

    @Autowired
    private AuditRecordRepository records;

    @Test
    void chainVerifiesAndDetectsTampering() {
        payments.ingest(request("RRN-301", PaymentEventType.AUTHORIZATION, 10_000));
        payments.ingest(request("RRN-301", PaymentEventType.SETTLEMENT, 10_000));

        assertThat(audit.verifyChain()).isTrue();

        var first = records.findAllByOrderBySequenceAsc().get(0);
        first.tamperPayloadForTest("tampered-payload");
        records.save(first);

        assertThat(audit.verifyChain()).isFalse();
    }

    private IngestPaymentEventRequest request(String rrn, PaymentEventType type, long amountCents) {
        return new IngestPaymentEventRequest(
                "TERM-001",
                "123456",
                rrn,
                type,
                amountCents,
                "NZD",
                Instant.parse("2026-11-04T00:00:00Z"),
                1,
                type + ":" + rrn + ":" + amountCents
        );
    }
}
