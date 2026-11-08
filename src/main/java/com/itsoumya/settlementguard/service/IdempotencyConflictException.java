package com.itsoumya.settlementguard.service;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.CONFLICT)
public class IdempotencyConflictException extends RuntimeException {

    public IdempotencyConflictException(String rrn, String eventType) {
        super("A different payload was already accepted for rrn=" + rrn + " and eventType=" + eventType + ".");
    }
}
