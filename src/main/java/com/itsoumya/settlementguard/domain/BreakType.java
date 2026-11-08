package com.itsoumya.settlementguard.domain;

public enum BreakType {
    MATCHED,
    MISSING_AUTHORIZATION,
    DUPLICATE_SETTLEMENT,
    AMOUNT_MISMATCH,
    DELAYED_SETTLEMENT
}
