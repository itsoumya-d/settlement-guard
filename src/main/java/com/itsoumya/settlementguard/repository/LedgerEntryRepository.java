package com.itsoumya.settlementguard.repository;

import com.itsoumya.settlementguard.domain.LedgerEntry;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

public interface LedgerEntryRepository extends JpaRepository<LedgerEntry, String> {

    List<LedgerEntry> findByEventIdOrderByPostedAtAsc(String eventId);

    @Query("select coalesce(sum(l.debitCents), 0) from LedgerEntry l")
    long totalDebits();

    @Query("select coalesce(sum(l.creditCents), 0) from LedgerEntry l")
    long totalCredits();
}
