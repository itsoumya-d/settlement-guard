package com.itsoumya.settlementguard.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "audit_records")
public class AuditRecord {

    @Id
    @Column(length = 36)
    private String id;

    @Column(nullable = false)
    private long sequence;

    @Column(name = "event_id", nullable = false, length = 36)
    private String eventId;

    @Column(name = "previous_hash", length = 64)
    private String previousHash;

    @Column(nullable = false, length = 64)
    private String hash;

    @Column(nullable = false, length = 1000)
    private String payload;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected AuditRecord() {
    }

    public AuditRecord(long sequence, String eventId, String previousHash, String hash, String payload, Instant createdAt) {
        this.sequence = sequence;
        this.eventId = eventId;
        this.previousHash = previousHash;
        this.hash = hash;
        this.payload = payload;
        this.createdAt = createdAt;
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

    public long getSequence() {
        return sequence;
    }

    public String getEventId() {
        return eventId;
    }

    public String getPreviousHash() {
        return previousHash;
    }

    public String getHash() {
        return hash;
    }

    public String getPayload() {
        return payload;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void tamperPayloadForTest(String payload) {
        this.payload = payload;
    }
}
