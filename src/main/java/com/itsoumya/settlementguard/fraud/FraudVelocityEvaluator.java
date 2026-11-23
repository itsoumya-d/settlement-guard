package com.itsoumya.settlementguard.fraud;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

public class FraudVelocityEvaluator {

    public record HistoricalAttempt(
        String deviceFingerprint,
        String cardHash,
        long amountCents,
        Instant timestamp,
        boolean wasSuccessful
    ) {}

    public FraudRiskAssessment evaluate(
        String deviceFingerprint,
        String cardHash,
        long amountCents,
        Instant currentTimestamp,
        List<HistoricalAttempt> recentAttempts
    ) {
        int score = 0;
        List<String> signals = new ArrayList<>();

        if (recentAttempts == null || recentAttempts.isEmpty()) {
            return new FraudRiskAssessment(0, FraudAction.ALLOW, List.of("NO_RECENT_HISTORY"));
        }

        Instant window10m = currentTimestamp.minus(Duration.ofMinutes(10));
        List<HistoricalAttempt> in10m = recentAttempts.stream()
            .filter(a -> !a.timestamp().isBefore(window10m))
            .toList();

        // 1. Device velocity check
        long sameDeviceCount = in10m.stream()
            .filter(a -> a.deviceFingerprint().equals(deviceFingerprint))
            .count();
        if (sameDeviceCount >= 10) {
            score += 65;
            signals.add("CRITICAL_DEVICE_VELOCITY_BURST");
        } else if (sameDeviceCount >= 5) {
            score += 35;
            signals.add("ELEVATED_DEVICE_VELOCITY");
        }

        // 2. Card cycling across distinct devices
        Set<String> distinctDevicesForCard = in10m.stream()
            .filter(a -> a.cardHash().equals(cardHash))
            .map(HistoricalAttempt::deviceFingerprint)
            .collect(Collectors.toSet());
        distinctDevicesForCard.add(deviceFingerprint);

        if (distinctDevicesForCard.size() >= 3) {
            score += 40;
            signals.add("CARD_CYCLING_ACROSS_DISTINCT_DEVICES");
        }

        // 3. Repeated rapid declines / card testing
        long recentFailures = in10m.stream()
            .filter(a -> a.deviceFingerprint().equals(deviceFingerprint) && !a.wasSuccessful())
            .count();
        if (recentFailures >= 3) {
            score += 30;
            signals.add("EXCESSIVE_DECLINE_CARD_TESTING_PATTERN");
        }

        // 4. Amount anomaly spike vs historical rolling average
        List<Long> historicalAmounts = recentAttempts.stream()
            .filter(HistoricalAttempt::wasSuccessful)
            .map(HistoricalAttempt::amountCents)
            .toList();
        if (historicalAmounts.size() >= 3) {
            double avg = historicalAmounts.stream().mapToLong(Long::longValue).average().orElse(0.0);
            if (avg > 0 && amountCents >= (avg * 5)) {
                score += 25;
                signals.add("UNUSUAL_AMOUNT_SPIKE_5X_HISTORICAL_AVERAGE");
            }
        }

        score = Math.min(100, Math.max(0, score));

        FraudAction action;
        if (score >= 75) {
            action = FraudAction.REJECT;
        } else if (score >= 40) {
            action = FraudAction.REVIEW;
        } else {
            action = FraudAction.ALLOW;
        }

        return new FraudRiskAssessment(score, action, signals);
    }
}
