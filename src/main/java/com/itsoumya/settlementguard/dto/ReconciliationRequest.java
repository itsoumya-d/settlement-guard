package com.itsoumya.settlementguard.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;

public record ReconciliationRequest(
        @NotBlank @Size(max = 160) String filename,
        @NotEmpty List<@Valid ReconciliationRow> rows
) {
}
