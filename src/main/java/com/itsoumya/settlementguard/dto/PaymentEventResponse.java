package com.itsoumya.settlementguard.dto;

import com.itsoumya.settlementguard.domain.PaymentEvent;

import java.time.Instant;

public record PaymentEventResponse(
        String id,
        String terminalId,
        String stan,
        String rrn,
        String eventType,
        long amountCents,
        String currency,
        Instant eventTime,
        long sequence,
        String status,
        String parkedReason,
        Instant receivedAt
) {
    public static PaymentEventResponse from(PaymentEvent event) {
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
                event.getStatus().name(),
                event.getParkedReason(),
                event.getReceivedAt()
        );
    }
}
