package com.itsoumya.settlementguard.repository;

import com.itsoumya.settlementguard.domain.BreakType;
import com.itsoumya.settlementguard.domain.ReconciliationBreak;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ReconciliationBreakRepository extends JpaRepository<ReconciliationBreak, String> {

    List<ReconciliationBreak> findByRunIdOrderByCreatedAtAsc(String runId);

    long countByBreakType(BreakType breakType);
}
