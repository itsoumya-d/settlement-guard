package com.itsoumya.settlementguard.service;

import com.itsoumya.settlementguard.audit.AuditChainService;
import com.itsoumya.settlementguard.domain.BreakType;
import com.itsoumya.settlementguard.domain.PaymentEvent;
import com.itsoumya.settlementguard.domain.PaymentEventStatus;
import com.itsoumya.settlementguard.domain.PaymentEventType;
import com.itsoumya.settlementguard.domain.ReconciliationBreak;
import com.itsoumya.settlementguard.domain.ReconciliationRun;
import com.itsoumya.settlementguard.dto.ReconciliationRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRow;
import com.itsoumya.settlementguard.dto.ReconciliationRunResponse;
import com.itsoumya.settlementguard.repository.PaymentEventRepository;
import com.itsoumya.settlementguard.repository.ReconciliationBreakRepository;
import com.itsoumya.settlementguard.repository.ReconciliationRunRepository;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class ReconciliationService {

    private final PaymentEventRepository events;
    private final ReconciliationRunRepository runs;
    private final ReconciliationBreakRepository breaks;
    private final AuditChainService audit;
    private final MeterRegistry meterRegistry;

    public ReconciliationService(
            PaymentEventRepository events,
            ReconciliationRunRepository runs,
            ReconciliationBreakRepository breaks,
            AuditChainService audit,
            MeterRegistry meterRegistry
    ) {
        this.events = events;
        this.runs = runs;
        this.breaks = breaks;
        this.audit = audit;
        this.meterRegistry = meterRegistry;
    }

    @Transactional
    public ReconciliationRunResponse run(ReconciliationRequest request) {
        ReconciliationRun run = runs.save(new ReconciliationRun(request.filename(), request.rows().size()));
        int matched = 0;
        int missing = 0;
        int duplicates = 0;
        int mismatches = 0;
        int delayed = 0;

        for (ReconciliationRow row : request.rows()) {
            List<PaymentEvent> found = events.findByRrnOrderByEventTimeAscSequenceAsc(row.rrn());
            List<PaymentEvent> authorizations = found.stream()
                    .filter(event -> event.getEventType() == PaymentEventType.AUTHORIZATION)
                    .filter(event -> event.getStatus() == PaymentEventStatus.APPLIED)
                    .toList();
            List<PaymentEvent> settlements = found.stream()
                    .filter(event -> event.getEventType() == PaymentEventType.SETTLEMENT
                            || event.getEventType() == PaymentEventType.CLEARING)
                    .filter(event -> event.getStatus() == PaymentEventStatus.APPLIED)
                    .toList();

            BreakType type;
            Long expected = row.amountCents();
            Long actual = null;
            String detail;

            if (authorizations.isEmpty()) {
                type = BreakType.MISSING_AUTHORIZATION;
                missing++;
                detail = "No applied authorization for rrn=" + row.rrn();
            } else if (settlements.size() > 1) {
                type = BreakType.DUPLICATE_SETTLEMENT;
                duplicates++;
                actual = settlements.get(0).getAmountCents();
                detail = "Multiple applied settlement events: " + settlements.size();
            } else if (settlements.isEmpty()) {
                type = BreakType.DELAYED_SETTLEMENT;
                delayed++;
                detail = "Authorization present but no settlement applied";
            } else if (settlements.get(0).getAmountCents() != row.amountCents()) {
                type = BreakType.AMOUNT_MISMATCH;
                mismatches++;
                actual = settlements.get(0).getAmountCents();
                detail = "Settlement amount does not match the submitted clearing amount";
            } else {
                type = BreakType.MATCHED;
                matched++;
                actual = row.amountCents();
                detail = "Matched";
            }

            breaks.save(new ReconciliationBreak(run.getId(), row.rrn(), type, expected, actual, detail));
            meterRegistry.counter("settlement_guard.reconciliation.breaks", "type", type.name()).increment();
        }

        run.complete(matched, missing, duplicates, mismatches, delayed);
        runs.save(run);
        audit.record(run.getId(), "reconciliation|" + request.filename() + "|" + matched + "|" + missing + "|"
                + duplicates + "|" + mismatches + "|" + delayed);

        return ReconciliationRunResponse.from(run, breaks.findByRunIdOrderByCreatedAtAsc(run.getId()));
    }

    @Transactional(readOnly = true)
    public ReconciliationRunResponse get(String id) {
        ReconciliationRun run = runs.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Unknown reconciliation run " + id + "."));
        return ReconciliationRunResponse.from(run, breaks.findByRunIdOrderByCreatedAtAsc(id));
    }
}
