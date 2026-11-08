package com.itsoumya.settlementguard.service;

import com.itsoumya.settlementguard.audit.AuditChainService;
import com.itsoumya.settlementguard.domain.LedgerEntry;
import com.itsoumya.settlementguard.domain.PaymentEvent;
import com.itsoumya.settlementguard.domain.PaymentEventStatus;
import com.itsoumya.settlementguard.domain.PaymentEventType;
import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import com.itsoumya.settlementguard.dto.PaymentEventResponse;
import com.itsoumya.settlementguard.repository.LedgerEntryRepository;
import com.itsoumya.settlementguard.repository.PaymentEventRepository;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class PaymentEventService {

    private final PaymentEventRepository events;
    private final LedgerEntryRepository ledger;
    private final AuditChainService audit;
    private final MeterRegistry meterRegistry;

    public PaymentEventService(
            PaymentEventRepository events,
            LedgerEntryRepository ledger,
            AuditChainService audit,
            MeterRegistry meterRegistry
    ) {
        this.events = events;
        this.ledger = ledger;
        this.audit = audit;
        this.meterRegistry = meterRegistry;
    }

    @Transactional
    public PaymentEventResponse ingest(IngestPaymentEventRequest request) {
        var existing = events.findByTerminalIdAndStanAndRrnAndEventType(
                request.terminalId(), request.stan(), request.rrn(), request.eventType());

        if (existing.isPresent()) {
            PaymentEvent event = existing.get();
            if (!event.getPayloadHash().equals(request.payloadHash())) {
                throw new IdempotencyConflictException(request.rrn(), request.eventType().name());
            }
            meterRegistry.counter("settlement_guard.events", "status", "DUPLICATE").increment();
            return duplicateResponse(event);
        }

        PaymentEvent event = new PaymentEvent(
                request.terminalId(),
                request.stan(),
                request.rrn(),
                request.eventType(),
                request.amountCents(),
                request.currency(),
                request.eventTime(),
                request.sequence(),
                request.payloadHash()
        );
        events.save(event);
        apply(event);
        events.save(event);
        audit.record(event.getId(), fingerprint(event));
        meterRegistry.counter("settlement_guard.events", "status", event.getStatus().name()).increment();

        return PaymentEventResponse.from(event);
    }

    @Transactional(readOnly = true)
    public List<PaymentEventResponse> recent(int limit) {
        int safeLimit = Math.max(1, Math.min(limit, 100));
        return events.findAll(PageRequest.of(0, safeLimit, Sort.by(Sort.Direction.DESC, "receivedAt")))
                .stream()
                .map(PaymentEventResponse::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<PaymentEventResponse> findByRrn(String rrn) {
        List<PaymentEvent> found = events.findByRrnOrderByEventTimeAscSequenceAsc(rrn);
        if (found.isEmpty()) {
            throw new ResourceNotFoundException("No payment events found for rrn=" + rrn + ".");
        }
        return found.stream().map(PaymentEventResponse::from).toList();
    }

    private void apply(PaymentEvent event) {
        switch (event.getEventType()) {
            case AUTHORIZATION -> {
                postAuthorization(event);
                event.markApplied();
                applyParkedSettlements(event.getRrn());
            }
            case CLEARING, SETTLEMENT -> {
                if (!hasAppliedAuthorization(event.getRrn())) {
                    event.markParked("AUTHORIZATION_NOT_SEEN");
                    meterRegistry.counter("settlement_guard.events", "status", "PARKED").increment();
                } else {
                    postSettlement(event);
                    event.markApplied();
                }
            }
            case REVERSAL, REFUND -> {
                if (!hasAppliedAuthorization(event.getRrn())) {
                    event.markParked("AUTHORIZATION_NOT_SEEN");
                    meterRegistry.counter("settlement_guard.events", "status", "PARKED").increment();
                } else {
                    postReversal(event);
                    event.markApplied();
                }
            }
        }
    }

    private void applyParkedSettlements(String rrn) {
        List<PaymentEvent> parked = events.findByRrnAndStatusOrderByEventTimeAscSequenceAsc(rrn, PaymentEventStatus.PARKED);
        for (PaymentEvent pending : parked) {
            if (pending.getEventType() == PaymentEventType.SETTLEMENT || pending.getEventType() == PaymentEventType.CLEARING) {
                postSettlement(pending);
                pending.markApplied();
                events.save(pending);
                audit.record(pending.getId(), fingerprint(pending));
                meterRegistry.counter("settlement_guard.events", "status", "APPLIED_AFTER_PARK").increment();
            }
        }
    }

    private boolean hasAppliedAuthorization(String rrn) {
        return events.findByRrnAndEventTypeOrderByEventTimeAscSequenceAsc(rrn, PaymentEventType.AUTHORIZATION)
                .stream()
                .anyMatch(event -> event.getStatus() == PaymentEventStatus.APPLIED);
    }

    private void postAuthorization(PaymentEvent event) {
        post(event, "MERCHANT_RECEIVABLE", "AUTHORIZATION_HOLD");
    }

    private void postSettlement(PaymentEvent event) {
        post(event, "SETTLEMENT_CLEARING", "MERCHANT_RECEIVABLE");
    }

    private void postReversal(PaymentEvent event) {
        post(event, "AUTHORIZATION_HOLD", "MERCHANT_RECEIVABLE");
    }

    private void post(PaymentEvent event, String debitAccount, String creditAccount) {
        ledger.save(new LedgerEntry(
                event.getId(), debitAccount, event.getAmountCents(), 0, event.getCurrency(),
                event.getEventType() + " debit"));
        ledger.save(new LedgerEntry(
                event.getId(), creditAccount, 0, event.getAmountCents(), event.getCurrency(),
                event.getEventType() + " credit"));
    }

    private PaymentEventResponse duplicateResponse(PaymentEvent event) {
        return new PaymentEventResponse(
                event.getId(),
                event.getTerminalId(),
                event.getStan(),
                event.getRrn(),
                event.getEventType().name(),
                event.getAmountCents(),
                event.getCurrency(),
                event.getEventTime(),
                event.getSequence(),
                "DUPLICATE",
                "IDEMPOTENT_REPLAY",
                event.getReceivedAt()
        );
    }

    private String fingerprint(PaymentEvent event) {
        return event.getEventType() + "|" + event.getRrn() + "|" + event.getAmountCents() + "|"
                + event.getCurrency() + "|" + event.getStatus();
    }
}
