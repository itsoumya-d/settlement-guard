package com.itsoumya.settlementguard;

import com.itsoumya.settlementguard.audit.AuditChainService;
import com.itsoumya.settlementguard.domain.LedgerEntry;
import com.itsoumya.settlementguard.domain.PaymentEventStatus;
import com.itsoumya.settlementguard.domain.PaymentEventType;
import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import com.itsoumya.settlementguard.repository.LedgerEntryRepository;
import com.itsoumya.settlementguard.repository.PaymentEventRepository;
import com.itsoumya.settlementguard.service.IdempotencyConflictException;
import com.itsoumya.settlementguard.service.PaymentEventService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class PaymentEventServiceTest {

    @Autowired
    private PaymentEventService service;

    @Autowired
    private PaymentEventRepository events;

    @Autowired
    private LedgerEntryRepository ledger;

    @Autowired
    private AuditChainService audit;

    @Test
    void authorizationAndSettlementProduceABalancedLedger() {
        var authorization = service.ingest(request(PaymentEventType.AUTHORIZATION, "RRN-001", 12_500));
        var settlement = service.ingest(request(PaymentEventType.SETTLEMENT, "RRN-001", 12_500));

        assertThat(debitsFor(authorization.id())).isEqualTo(12_500);
        assertThat(creditsFor(authorization.id())).isEqualTo(12_500);
        assertThat(debitsFor(settlement.id())).isEqualTo(12_500);
        assertThat(ledger.totalDebits()).isEqualTo(ledger.totalCredits());
        assertThat(events.findByRrnOrderByEventTimeAscSequenceAsc("RRN-001"))
                .allMatch(event -> event.getStatus() == PaymentEventStatus.APPLIED);
        assertThat(audit.verifyChain()).isTrue();
    }

    @Test
    void duplicateEventIsIdempotentAndDoesNotDoublePost() {
        var request = request(PaymentEventType.AUTHORIZATION, "RRN-002", 8_000);

        var first = service.ingest(request);
        var second = service.ingest(request);

        assertThat(first.status()).isEqualTo("APPLIED");
        assertThat(second.status()).isEqualTo("DUPLICATE");
        assertThat(events.findByRrnOrderByEventTimeAscSequenceAsc("RRN-002")).hasSize(1);
        assertThat(ledger.findByEventIdOrderByPostedAtAsc(first.id())).hasSize(2);
        assertThat(debitsFor(first.id())).isEqualTo(8_000);
    }

    @Test
    void sameIdempotencyKeyWithDifferentPayloadIsAConflict() {
        service.ingest(request(PaymentEventType.AUTHORIZATION, "RRN-003", 8_000));

        assertThatThrownBy(() -> service.ingest(request(PaymentEventType.AUTHORIZATION, "RRN-003", 9_000)))
                .isInstanceOf(IdempotencyConflictException.class);
    }

    @Test
    void settlementThatArrivesBeforeAuthorizationIsParkedThenApplied() {
        var settlement = service.ingest(request(PaymentEventType.SETTLEMENT, "RRN-004", 15_000));
        assertThat(settlement.status()).isEqualTo("PARKED");
        assertThat(settlement.parkedReason()).isEqualTo("AUTHORIZATION_NOT_SEEN");

        service.ingest(request(PaymentEventType.AUTHORIZATION, "RRN-004", 15_000));

        assertThat(events.findByRrnOrderByEventTimeAscSequenceAsc("RRN-004"))
                .allMatch(event -> event.getStatus() == PaymentEventStatus.APPLIED);
        assertThat(ledger.totalDebits()).isEqualTo(ledger.totalCredits());
    }

    @Test
    void reversalWithoutAuthorizationIsParked() {
        var reversal = service.ingest(request(PaymentEventType.REVERSAL, "RRN-005", 3_000));

        assertThat(reversal.status()).isEqualTo("PARKED");
        assertThat(reversal.parkedReason()).isEqualTo("AUTHORIZATION_NOT_SEEN");
    }

    private long debitsFor(String eventId) {
        return ledger.findByEventIdOrderByPostedAtAsc(eventId).stream().mapToLong(LedgerEntry::getDebitCents).sum();
    }

    private long creditsFor(String eventId) {
        return ledger.findByEventIdOrderByPostedAtAsc(eventId).stream().mapToLong(LedgerEntry::getCreditCents).sum();
    }

    private IngestPaymentEventRequest request(PaymentEventType type, String rrn, long amountCents) {
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
