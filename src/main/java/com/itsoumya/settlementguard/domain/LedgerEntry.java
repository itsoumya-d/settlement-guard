package com.itsoumya.settlementguard.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "ledger_entries")
public class LedgerEntry {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "event_id", nullable = false, length = 36)
    private String eventId;

    @Column(nullable = false, length = 64)
    private String account;

    @Column(name = "debit_cents", nullable = false)
    private long debitCents;

    @Column(name = "credit_cents", nullable = false)
    private long creditCents;

    @Column(nullable = false, length = 3)
    private String currency;

    @Column(name = "posted_at", nullable = false)
    private Instant postedAt;

    @Column(length = 160)
    private String description;

    protected LedgerEntry() {
    }

    public LedgerEntry(
            String eventId,
            String account,
            long debitCents,
            long creditCents,
            String currency,
            String description
    ) {
        this.eventId = eventId;
        this.account = account;
        this.debitCents = debitCents;
        this.creditCents = creditCents;
        this.currency = currency;
        this.description = description;
        this.postedAt = Instant.now();
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

    public String getEventId() {
        return eventId;
    }

    public String getAccount() {
        return account;
    }

    public long getDebitCents() {
        return debitCents;
    }

    public long getCreditCents() {
        return creditCents;
    }

    public String getCurrency() {
        return currency;
    }

    public Instant getPostedAt() {
        return postedAt;
    }

    public String getDescription() {
        return description;
    }
}
