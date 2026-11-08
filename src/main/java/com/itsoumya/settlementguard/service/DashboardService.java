package com.itsoumya.settlementguard.service;

import com.itsoumya.settlementguard.domain.PaymentEventStatus;
import com.itsoumya.settlementguard.domain.ReconciliationRun;
import com.itsoumya.settlementguard.dto.DashboardSummary;
import com.itsoumya.settlementguard.repository.LedgerEntryRepository;
import com.itsoumya.settlementguard.repository.PaymentEventRepository;
import com.itsoumya.settlementguard.repository.ReconciliationBreakRepository;
import com.itsoumya.settlementguard.repository.ReconciliationRunRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DashboardService {

    private final PaymentEventRepository events;
    private final LedgerEntryRepository ledger;
    private final ReconciliationRunRepository runs;
    private final ReconciliationBreakRepository breaks;

    public DashboardService(
            PaymentEventRepository events,
            LedgerEntryRepository ledger,
            ReconciliationRunRepository runs,
            ReconciliationBreakRepository breaks
    ) {
        this.events = events;
        this.ledger = ledger;
        this.runs = runs;
        this.breaks = breaks;
    }

    @Transactional(readOnly = true)
    public DashboardSummary summary() {
        long debits = ledger.totalDebits();
        long credits = ledger.totalCredits();
        var latest = runs.findFirstByOrderByStartedAtDesc();

        return new DashboardSummary(
                new DashboardSummary.EventCounts(
                        events.count(),
                        events.countByStatus(PaymentEventStatus.APPLIED),
                        events.countByStatus(PaymentEventStatus.PARKED),
                        events.countByStatus(PaymentEventStatus.DUPLICATE)
                ),
                new DashboardSummary.LedgerBalance(debits, credits, debits == credits),
                new DashboardSummary.ReconciliationSummary(
                        runs.count(),
                        breaks.count(),
                        latest.map(ReconciliationRun::getId).orElse(null),
                        latest.map(run -> run.getStatus().name()).orElse(null),
                        latest.map(ReconciliationRun::getCompletedAt).orElse(null)
                )
        );
    }
}
