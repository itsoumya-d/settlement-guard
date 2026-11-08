package com.itsoumya.settlementguard.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "reconciliation_breaks")
public class ReconciliationBreak {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "run_id", nullable = false, length = 36)
    private String runId;

    @Column(nullable = false, length = 32)
    private String rrn;

    @Enumerated(EnumType.STRING)
    @Column(name = "break_type", nullable = false, length = 32)
    private BreakType breakType;

    @Column(name = "expected_cents")
    private Long expectedCents;

    @Column(name = "actual_cents")
    private Long actualCents;

    @Column(length = 255)
    private String detail;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected ReconciliationBreak() {
    }

    public ReconciliationBreak(
            String runId,
            String rrn,
            BreakType breakType,
            Long expectedCents,
            Long actualCents,
            String detail
    ) {
        this.runId = runId;
        this.rrn = rrn;
        this.breakType = breakType;
        this.expectedCents = expectedCents;
        this.actualCents = actualCents;
        this.detail = detail;
        this.createdAt = Instant.now();
    }

    @PrePersist
    void ensureId() {
        if (id == null) {
            id = UUID.randomUUID().toString();
        }
    }

    public String getId() {
        return id;
    }

    public String getRunId() {
        return runId;
    }

    public String getRrn() {
        return rrn;
    }

    public BreakType getBreakType() {
        return breakType;
    }

    public Long getExpectedCents() {
        return expectedCents;
    }

    public Long getActualCents() {
        return actualCents;
    }

    public String getDetail() {
        return detail;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
