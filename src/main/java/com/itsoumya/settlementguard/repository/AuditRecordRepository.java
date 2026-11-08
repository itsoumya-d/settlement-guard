package com.itsoumya.settlementguard.repository;

import com.itsoumya.settlementguard.domain.AuditRecord;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AuditRecordRepository extends JpaRepository<AuditRecord, String> {

    List<AuditRecord> findAllByOrderBySequenceAsc();

    Optional<AuditRecord> findFirstByOrderBySequenceDesc();
}
