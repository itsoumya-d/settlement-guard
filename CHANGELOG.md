# Changelog

## [1.0.0] - 2026-11-04

### Added

- Java 17 / Spring Boot payment event API with idempotency, parking and double-entry ledger.
- Kafka-ready consumer, MySQL/Flyway schema and Testcontainers MySQL integration.
- Reconciliation service with five explicit break classifications.
- Independent Python reconciliation CLI and pytest suite.
- SHA-256 hash-chained audit records with sequence ordering.
- Paymark-token operations dashboard (Roboto, `#d9291c`, `#e6746b`, `#1e1e1e`, 5px radius).
- Terraform SQS/DLQ/SNS/CloudWatch alarms.
- Docker, Docker Compose, Kubernetes deployment/service/HPA.
- GitHub Actions CI across Java 17/21, Python 3.11/3.12, Terraform and Docker.
- Public incident evidence, architecture, design-token and evidence-matrix docs.
