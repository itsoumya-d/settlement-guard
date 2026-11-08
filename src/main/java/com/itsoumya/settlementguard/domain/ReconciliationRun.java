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
@Table(name = "reconciliation_runs")
public class ReconciliationRun {

    public enum Status {
        RUNNING,
        COMPLETED,
        FAILED
    }

    @Id
    @Column(length = 36)
    private String id;

    @Column(nullable = false, length = 160)
    private String filename;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 24)
    private Status status;

    @Column(nullable = false)
    private int totalRows;

    @Column(nullable = false)
    private int matched;

    @Column(name = "missing_authorization", nullable = false)
    private int missingAuthorization;

    @Column(name = "duplicate_settlements", nullable = false)
    private int duplicateSettlements;

    @Column(name = "amount_mismatches", nullable = false)
    private int amountMismatches;

    @Column(name = "delayed_settlements", nullable = false)
    private int delayedSettlements;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    protected ReconciliationRun() {
    }

    public ReconciliationRun(String filename, int totalRows) {
        this.filename = filename;
        this.status = Status.RUNNING;
        this.totalRows = totalRows;
        this.startedAt = Instant.now();
    }

    @PrePersist
    void ensureId() {
        if (id == null) {
            id = UUID.randomUUID().toString();
        }
    }

    public void complete(
            int matched,
            int missingAuthorization,
            int duplicateSettlements,
            int amountMismatches,
            int delayedSettlements
    ) {
        this.matched = matched;
        this.missingAuthorization = missingAuthorization;
        this.duplicateSettlements = duplicateSettlements;
        this.amountMismatches = amountMismatches;
        this.delayedSettlements = delayedSettlements;
        this.status = Status.COMPLETED;
        this.completedAt = Instant.now();
    }

    public String getId() {
        return id;
    }

    public String getFilename() {
        return filename;
    }

    public Status getStatus() {
        return status;
    }

    public int getTotalRows() {
        return totalRows;
    }

    public int getMatched() {
        return matched;
    }

    public int getMissingAuthorization() {
        return missingAuthorization;
    }

    public int getDuplicateSettlements() {
        return duplicateSettlements;
    }

    public int getAmountMismatches() {
        return amountMismatches;
    }

    public int getDelayedSettlements() {
        return delayedSettlements;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getCompletedAt() {
        return completedAt;
    }
}
