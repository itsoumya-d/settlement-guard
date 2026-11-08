package com.itsoumya.settlementguard.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "payment_events", uniqueConstraints = @UniqueConstraint(
        name = "uk_payment_event",
        columnNames = {"terminal_id", "stan", "rrn", "event_type"}
))
public class PaymentEvent {

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "terminal_id", nullable = false, length = 32)
    private String terminalId;

    @Column(nullable = false, length = 12)
    private String stan;

    @Column(nullable = false, length = 32)
    private String rrn;

    @Enumerated(EnumType.STRING)
    @Column(name = "event_type", nullable = false, length = 32)
    private PaymentEventType eventType;

    @Column(name = "amount_cents", nullable = false)
    private long amountCents;

    @Column(nullable = false, length = 3)
    private String currency;

    @Column(name = "event_time", nullable = false)
    private Instant eventTime;

    @Column(name = "sequence_no", nullable = false)
    private long sequence;

    @Column(name = "payload_hash", nullable = false, length = 128)
    private String payloadHash;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 24)
    private PaymentEventStatus status;

    @Column(name = "parked_reason", length = 120)
    private String parkedReason;

    @Column(name = "received_at", nullable = false)
    private Instant receivedAt;

    @Version
    private long version;

    protected PaymentEvent() {
    }

    public PaymentEvent(
            String terminalId,
            String stan,
            String rrn,
            PaymentEventType eventType,
            long amountCents,
            String currency,
            Instant eventTime,
            long sequence,
            String payloadHash
    ) {
        this.terminalId = terminalId;
        this.stan = stan;
        this.rrn = rrn;
        this.eventType = eventType;
        this.amountCents = amountCents;
        this.currency = currency;
        this.eventTime = eventTime;
        this.sequence = sequence;
        this.payloadHash = payloadHash;
        this.status = PaymentEventStatus.RECEIVED;
        this.receivedAt = Instant.now();
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

    public String getTerminalId() {
        return terminalId;
    }

    public String getStan() {
        return stan;
    }

    public String getRrn() {
        return rrn;
    }

    public PaymentEventType getEventType() {
        return eventType;
    }

    public long getAmountCents() {
        return amountCents;
    }

    public String getCurrency() {
        return currency;
    }

    public Instant getEventTime() {
        return eventTime;
    }

    public long getSequence() {
        return sequence;
    }

    public String getPayloadHash() {
        return payloadHash;
    }

    public PaymentEventStatus getStatus() {
        return status;
    }

    public String getParkedReason() {
        return parkedReason;
    }

    public Instant getReceivedAt() {
        return receivedAt;
    }

    public void markApplied() {
        this.status = PaymentEventStatus.APPLIED;
        this.parkedReason = null;
    }

    public void markParked(String reason) {
        this.status = PaymentEventStatus.PARKED;
        this.parkedReason = reason;
    }

    public void markDuplicate() {
        this.status = PaymentEventStatus.DUPLICATE;
    }
}
