package com.itsoumya.settlementguard;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class PaymentEventControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void validEventReturnsCreated() throws Exception {
        mockMvc.perform(post("/api/v1/payments/events")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body("RRN-201", "AUTHORIZATION", 10_000)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.rrn").value("RRN-201"))
                .andExpect(jsonPath("$.status").value("APPLIED"));
    }

    @Test
    void replayingTheSamePayloadReturnsOkAndDuplicate() throws Exception {
        String payload = body("RRN-202", "AUTHORIZATION", 10_000);

        mockMvc.perform(post("/api/v1/payments/events").contentType(MediaType.APPLICATION_JSON).content(payload))
                .andExpect(status().isCreated());
        mockMvc.perform(post("/api/v1/payments/events").contentType(MediaType.APPLICATION_JSON).content(payload))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("DUPLICATE"));
    }

    @Test
    void invalidPayloadReturnsUnprocessableEntity() throws Exception {
        mockMvc.perform(post("/api/v1/payments/events")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body("RRN-203", "AUTHORIZATION", 0)))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.message").value("Request validation failed."));
    }

    @Test
    void eventsCanBeReadByRrnAndRecent() throws Exception {
        mockMvc.perform(post("/api/v1/payments/events")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body("RRN-204", "AUTHORIZATION", 10_000)))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/api/v1/payments/RRN-204"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].rrn").value("RRN-204"));

        mockMvc.perform(get("/api/v1/payments?limit=5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray());
    }

    @Test
    void dashboardSummaryIsAvailable() throws Exception {
        mockMvc.perform(get("/api/v1/dashboard/summary"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.events").exists())
                .andExpect(jsonPath("$.ledger.balanced").value(true));
    }

    private String body(String rrn, String type, long amount) {
        return """
                {
                  "terminalId": "TERM-001",
                  "stan": "123456",
                  "rrn": "%s",
                  "eventType": "%s",
                  "amountCents": %d,
                  "currency": "NZD",
                  "eventTime": "2026-11-04T00:00:00Z",
                  "sequence": 1,
                  "payloadHash": "%s"
                }
                """.formatted(rrn, type, amount, type + ":" + rrn + ":" + amount);
    }
}
