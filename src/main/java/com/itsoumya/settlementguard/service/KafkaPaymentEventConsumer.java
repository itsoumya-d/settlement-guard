package com.itsoumya.settlementguard.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.itsoumya.settlementguard.dto.IngestPaymentEventRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.stereotype.Component;

@Component
public class KafkaPaymentEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(KafkaPaymentEventConsumer.class);

    private final PaymentEventService paymentEvents;
    private final ObjectMapper objectMapper;

    public KafkaPaymentEventConsumer(PaymentEventService paymentEvents, ObjectMapper objectMapper) {
        this.paymentEvents = paymentEvents;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(
            topics = "${app.kafka.topic:payment-events}",
            groupId = "settlement-guard",
            autoStartup = "${app.kafka.enabled:false}"
    )
    public void consume(String payload, @Header(KafkaHeaders.RECEIVED_KEY) String key) {
        try {
            IngestPaymentEventRequest request = objectMapper.readValue(payload, IngestPaymentEventRequest.class);
            paymentEvents.ingest(request);
            log.info("Processed Kafka payment event key={} rrn={}", key, request.rrn());
        } catch (Exception exception) {
            log.error("Rejected Kafka payment event key={} reason={}", key, exception.getMessage());
            throw new IllegalStateException("Kafka payment event rejected", exception);
        }
    }
}
