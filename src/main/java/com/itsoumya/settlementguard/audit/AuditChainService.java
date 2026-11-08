package com.itsoumya.settlementguard.audit;

import com.itsoumya.settlementguard.domain.AuditRecord;
import com.itsoumya.settlementguard.repository.AuditRecordRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.List;

@Service
public class AuditChainService {

    private final AuditRecordRepository records;

    public AuditChainService(AuditRecordRepository records) {
        this.records = records;
    }

    @Transactional
    public AuditRecord record(String eventId, String payload) {
        String previous = records.findFirstByOrderBySequenceDesc()
                .map(AuditRecord::getHash)
                .orElse(null);
        long sequence = records.findFirstByOrderBySequenceDesc()
                .map(record -> record.getSequence() + 1)
                .orElse(1L);
        Instant createdAt = Instant.now().truncatedTo(ChronoUnit.SECONDS);
        String hash = sha256(previous + "|" + sequence + "|" + eventId + "|" + payload + "|" + createdAt);
        return records.save(new AuditRecord(sequence, eventId, previous, hash, payload, createdAt));
    }

    @Transactional(readOnly = true)
    public boolean verifyChain() {
        List<AuditRecord> all = records.findAllByOrderBySequenceAsc();
        String previous = null;
        for (AuditRecord record : all) {
            Instant createdAt = record.getCreatedAt().truncatedTo(ChronoUnit.SECONDS);
            String expected = sha256(previous + "|" + record.getSequence() + "|" + record.getEventId() + "|" + record.getPayload() + "|" + createdAt);
            if (!MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), record.getHash().getBytes(StandardCharsets.UTF_8))) {
                return false;
            }
            previous = record.getHash();
        }
        return true;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is not available.", exception);
        }
    }
}
