package com.itsoumya.settlementguard.dto;

import com.itsoumya.settlementguard.domain.ReconciliationBreak;
import com.itsoumya.settlementguard.domain.ReconciliationRun;

import java.time.Instant;
import java.util.List;

public record ReconciliationRunResponse(
        String id,
        String filename,
        String status,
        int totalRows,
        int matched,
        int missingAuthorization,
        int duplicateSettlements,
        int amountMismatches,
        int delayedSettlements,
        Instant startedAt,
        Instant completedAt,
        List<BreakResponse> breaks
) {
    public record BreakResponse(
            String rrn,
            String breakType,
            Long expectedCents,
            Long actualCents,
            String detail,
            Instant createdAt
    ) {
        public static BreakResponse from(ReconciliationBreak value) {
            return new BreakResponse(
                    value.getRrn(),
                    value.getBreakType().name(),
                    value.getExpectedCents(),
                    value.getActualCents(),
                    value.getDetail(),
                    value.getCreatedAt()
            );
        }
    }

    public static ReconciliationRunResponse from(ReconciliationRun run, List<ReconciliationBreak> breaks) {
        return new ReconciliationRunResponse(
                run.getId(),
                run.getFilename(),
                run.getStatus().name(),
                run.getTotalRows(),
                run.getMatched(),
                run.getMissingAuthorization(),
                run.getDuplicateSettlements(),
                run.getAmountMismatches(),
                run.getDelayedSettlements(),
                run.getStartedAt(),
                run.getCompletedAt(),
                breaks.stream().map(BreakResponse::from).toList()
        );
    }
}
