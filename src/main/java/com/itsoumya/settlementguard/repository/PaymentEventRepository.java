package com.itsoumya.settlementguard.repository;

import com.itsoumya.settlementguard.domain.PaymentEvent;
import com.itsoumya.settlementguard.domain.PaymentEventStatus;
import com.itsoumya.settlementguard.domain.PaymentEventType;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface PaymentEventRepository extends JpaRepository<PaymentEvent, String> {

    Optional<PaymentEvent> findByTerminalIdAndStanAndRrnAndEventType(
            String terminalId,
            String stan,
            String rrn,
            PaymentEventType eventType
    );

    List<PaymentEvent> findByRrnOrderByEventTimeAscSequenceAsc(String rrn);

    List<PaymentEvent> findByRrnAndStatusOrderByEventTimeAscSequenceAsc(String rrn, PaymentEventStatus status);

    List<PaymentEvent> findByRrnAndEventTypeOrderByEventTimeAscSequenceAsc(String rrn, PaymentEventType eventType);

    long countByStatus(PaymentEventStatus status);
}
