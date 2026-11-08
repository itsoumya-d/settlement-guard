package com.itsoumya.settlementguard.repository;

import com.itsoumya.settlementguard.domain.ReconciliationRun;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface ReconciliationRunRepository extends JpaRepository<ReconciliationRun, String> {

    Optional<ReconciliationRun> findFirstByOrderByStartedAtDesc();
}
