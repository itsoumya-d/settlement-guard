package com.itsoumya.settlementguard;

import com.itsoumya.settlementguard.domain.PaymentEventType;
import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRequest;
import com.itsoumya.settlementguard.dto.ReconciliationRow;
import com.itsoumya.settlementguard.service.PaymentEventService;
import com.itsoumya.settlementguard.service.ReconciliationService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MySQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.NONE)
@ActiveProfiles("mysql")
@Testcontainers(disabledWithoutDocker = true)
class SettlementGuardIntegrationTest {

    @Container
    static final MySQLContainer<?> MYSQL = new MySQLContainer<>("mysql:8.0");

    @DynamicPropertySource
    static void databaseProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", MYSQL::getJdbcUrl);
        registry.add("spring.datasource.username", MYSQL::getUsername);
        registry.add("spring.datasource.password", MYSQL::getPassword);
        registry.add("spring.jpa.hibernate.ddl-auto", () -> "validate");
        registry.add("spring.flyway.enabled", () -> "true");
    }

    @Autowired
    private PaymentEventService payments;

    @Autowired
    private ReconciliationService reconciliation;

    @Test
    void flywaySchemaAndEndToEndFlowWorkAgainstMysql8() {
        payments.ingest(new IngestPaymentEventRequest(
                "TERM-INT", "123456", "RRN-INT-1", PaymentEventType.AUTHORIZATION,
                25_000, "NZD", Instant.parse("2026-11-04T00:00:00Z"), 1, "int-auth"));

        payments.ingest(new IngestPaymentEventRequest(
                "TERM-INT", "123456", "RRN-INT-1", PaymentEventType.SETTLEMENT,
                25_000, "NZD", Instant.parse("2026-11-04T00:01:00Z"), 2, "int-settle"));

        var run = reconciliation.run(new ReconciliationRequest("mysql-settlement.csv", List.of(
                new ReconciliationRow("RRN-INT-1", 25_000, "NZD", Instant.parse("2026-11-04T02:00:00Z"), "TERM-INT", "123456")
        )));

        assertThat(run.matched()).isEqualTo(1);
        assertThat(run.breaks()).extracting("breakType").containsExactly("MATCHED");
    }
}
