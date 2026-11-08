package com.itsoumya.settlementguard.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.Instant;

public record ReconciliationRow(
        @NotBlank @Size(max = 32) String rrn,
        @Min(1) long amountCents,
        @NotBlank @Size(min = 3, max = 3) String currency,
        @NotNull Instant settledAt,
        @Size(max = 32) String terminalId,
        @Size(max = 12) String stan
) {
}
