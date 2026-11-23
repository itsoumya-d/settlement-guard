package com.itsoumya.settlementguard.fraud;

import java.util.Collections;
import java.util.List;

public record FraudRiskAssessment(
    int riskScore,
    FraudAction action,
    List<String> signals
) {
    public FraudRiskAssessment {
        if (riskScore < 0 || riskScore > 100) {
            throw new IllegalArgumentException("Risk score must be between 0 and 100");
        }
        signals = signals != null ? List.copyOf(signals) : Collections.emptyList();
    }
}
