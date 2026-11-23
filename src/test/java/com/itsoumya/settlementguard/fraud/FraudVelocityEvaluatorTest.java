package com.itsoumya.settlementguard.fraud;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class FraudVelocityEvaluatorTest {

    private FraudVelocityEvaluator evaluator;
    private Instant now;

    @BeforeEach
    void setUp() {
        evaluator = new FraudVelocityEvaluator();
        now = Instant.parse("2026-11-23T10:00:00Z");
    }

    @Test
    void shouldAllowWhenNoRecentHistory() {
        FraudRiskAssessment result = evaluator.evaluate(
            "device_01", "card_hash_abc", 2500, now, List.of()
        );
        assertEquals(0, result.riskScore());
        assertEquals(FraudAction.ALLOW, result.action());
        assertTrue(result.signals().contains("NO_RECENT_HISTORY"));
    }

    @Test
    void shouldTriggerReviewOnElevatedDeviceVelocity() {
        List<FraudVelocityEvaluator.HistoricalAttempt> history = new ArrayList<>();
        for (int i = 1; i <= 6; i++) {
            history.add(new FraudVelocityEvaluator.HistoricalAttempt(
                "device_01", "card_hash_abc", 2000, now.minus(Duration.ofMinutes(i)), true
            ));
        }

        FraudRiskAssessment result = evaluator.evaluate(
            "device_01", "card_hash_abc", 2000, now, history
        );
        assertEquals(35, result.riskScore());
        assertEquals(FraudAction.ALLOW, result.action());
        assertTrue(result.signals().contains("ELEVATED_DEVICE_VELOCITY"));
    }

    @Test
    void shouldRejectOnCardCyclingAndRepeatedFailures() {
        List<FraudVelocityEvaluator.HistoricalAttempt> history = List.of(
            new FraudVelocityEvaluator.HistoricalAttempt("device_02", "card_hash_stolen", 1000, now.minus(Duration.ofMinutes(8)), false),
            new FraudVelocityEvaluator.HistoricalAttempt("device_03", "card_hash_stolen", 1000, now.minus(Duration.ofMinutes(6)), false),
            new FraudVelocityEvaluator.HistoricalAttempt("device_01", "card_hash_stolen", 1000, now.minus(Duration.ofMinutes(4)), false),
            new FraudVelocityEvaluator.HistoricalAttempt("device_01", "card_hash_stolen", 1000, now.minus(Duration.ofMinutes(2)), false),
            new FraudVelocityEvaluator.HistoricalAttempt("device_01", "card_hash_stolen", 1000, now.minus(Duration.ofMinutes(1)), false)
        );

        FraudRiskAssessment result = evaluator.evaluate(
            "device_01", "card_hash_stolen", 1000, now, history
        );
        // Card cycling (3 devices: 02, 03, 01) -> +40
        // Rapid failures on device_01 (3 failures) -> +30
        // Elevated device velocity (3 on device 01, not >= 5) -> 0
        // Total score = 70 -> REVIEW
        assertEquals(70, result.riskScore());
        assertEquals(FraudAction.REVIEW, result.action());
        assertTrue(result.signals().contains("CARD_CYCLING_ACROSS_DISTINCT_DEVICES"));
        assertTrue(result.signals().contains("EXCESSIVE_DECLINE_CARD_TESTING_PATTERN"));
    }

    @Test
    void shouldRejectWhenCriticalVelocityAndAmountSpike() {
        List<FraudVelocityEvaluator.HistoricalAttempt> history = new ArrayList<>();
        // 10 prior attempts on device_01
        for (int i = 1; i <= 10; i++) {
            history.add(new FraudVelocityEvaluator.HistoricalAttempt(
                "device_01", "card_hash_xyz", 1000, now.minus(Duration.ofMinutes(i)), true
            ));
        }

        // Current attempt is 50,000 cents (50x average of 1,000 cents)
        FraudRiskAssessment result = evaluator.evaluate(
            "device_01", "card_hash_xyz", 50000, now, history
        );
        // Critical device burst -> +65
        // Amount spike 5x -> +25
        // Total score = 90 -> REJECT
        assertEquals(90, result.riskScore());
        assertEquals(FraudAction.REJECT, result.action());
        assertTrue(result.signals().contains("CRITICAL_DEVICE_VELOCITY_BURST"));
        assertTrue(result.signals().contains("UNUSUAL_AMOUNT_SPIKE_5X_HISTORICAL_AVERAGE"));
    }
}
