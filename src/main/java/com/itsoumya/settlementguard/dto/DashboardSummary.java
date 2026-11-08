package com.itsoumya.settlementguard.dto;

import java.time.Instant;

public record DashboardSummary(
        EventCounts events,
        LedgerBalance ledger,
        ReconciliationSummary reconciliation
) {
    public record EventCounts(long total, long applied, long parked, long duplicate) {
    }

    public record LedgerBalance(long debits, long credits, boolean balanced) {
    }

    public record ReconciliationSummary(
            long runs,
            long breaks,
            String latestRunId,
            String latestStatus,
            Instant latestCompletedAt
    ) {
    }
}
