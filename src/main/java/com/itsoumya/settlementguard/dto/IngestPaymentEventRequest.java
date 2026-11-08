package com.itsoumya.settlementguard.dto;

import com.itsoumya.settlementguard.domain.PaymentEventType;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.time.Instant;

public record IngestPaymentEventRequest(
        @NotBlank @Size(max = 32) String terminalId,
        @NotBlank @Size(min = 6, max = 12) String stan,
        @NotBlank @Size(max = 32) String rrn,
        @NotNull PaymentEventType eventType,
        @Min(1) @Max(100_000_000) long amountCents,
        @NotBlank @Pattern(regexp = "[A-Z]{3}") String currency,
        @NotNull Instant eventTime,
        @Min(1) long sequence,
        @NotBlank @Size(max = 128) String payloadHash
) {
}
