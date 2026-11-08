# Evidence matrix

| Requirement | Status | Implementation | Proof |
| --- | --- | --- | --- |
| Java 17 | Implemented | `build.gradle`, Java sources, Gradle wrapper | `./gradlew test` |
| Spring Boot | Implemented | Spring Web, Validation, Data JPA, Actuator | `SettlementGuardApplication`; context tests |
| AWS | Implemented | Terraform SQS/DLQ/SNS/CloudWatch; container/K8s manifests | `infra/terraform/`; `.github/workflows/ci.yml` terraform job |
| MySQL | Implemented | Flyway `V1__init.sql`; MySQL 8 Testcontainers integration | `SettlementGuardIntegrationTest` |
| Python | Implemented | Independent reconciliation CLI | `tools/reconcile.py`; `tools/test_reconcile.py` (6 tests) |
| Kafka | Implemented | `KafkaPaymentEventConsumer`; Redpanda in Compose | `KafkaPaymentEventConsumer`; `docker-compose.yml` |
| HTTP / REST | Implemented | Payment, reconciliation and dashboard APIs | `PaymentEventControllerTest` |
| Payments reliability | Implemented | Parking, idempotency, double-entry ledger, reconciliation | `PaymentEventServiceTest`, `ReconciliationServiceTest` |
| Out-of-order settlement | Implemented | `AUTHORIZATION_NOT_SEEN` parking and automatic replay | `settlementThatArrivesBeforeAuthorizationIsParkedThenApplied` |
| Duplicate settlement prevention | Implemented | Unique natural key + payload hash + reconciliation duplicate class | `duplicateEventIsIdempotent...`; `duplicateSettlementIsExplicit` |
| Reconciliation | Implemented | Five explicit classifications | `ReconciliationServiceTest`; Python CLI tests |
| Audit trail | Implemented | SHA-256 hash chain with sequence ordering | `AuditChainTest` |
| Observability | Implemented | Micrometer counters, Prometheus, health/readiness | Actuator config; `PaymentEventService` |
| Design-token parity | Implemented | Paymark Roboto/red/salmon/ink/5px tokens in UI | `docs/design-tokens.md`; `styles.css` |
| CI/CD | Implemented | GitHub Actions Java 17/21, Python 3.11/3.12, Terraform, Docker | `.github/workflows/ci.yml` |
| Docker | Implemented | Multi-stage `Dockerfile`, Compose with MySQL/Redpanda | `Dockerfile`, `docker-compose.yml` |
| Kubernetes | Implemented | Deployment, Service, HPA, config/secret examples | `k8s/` |
| Automated tests | Implemented | 17 Java tests (16 local + MySQL integration when Docker is available) + 6 Python tests | `./gradlew test`, `python -m pytest tools -q` |
| Live Paymark API | Not claimed | No credentials or production access | Documented limitation |
| PCI-DSS / HSM | Not claimed | Public reference build only | Documented limitation |
| Proprietary code | Not used | Clean-room from public sources | `README.md`, `docs/pain-point.md` |

## Interview talking points

1. **Parking is a state, not an exception** — a settlement that arrives before authorization is retained and replayed.
2. **Idempotency has two layers** — natural key plus payload hash; same key/different payload returns 409.
3. **Reconciliation is explicit** — missing, duplicate, mismatch and delayed are separate break types.
4. **The ledger must balance** — every event posts two entries; the dashboard exposes the totals.
5. **The audit trail is ordered** — sequence numbers make the hash chain deterministic across databases.
6. **The Python control is independent** — a second implementation catches logic drift.
7. **The UI matches the company's tokens** — Roboto, `#d9291c`, `#e6746b`, `#1e1e1e`, 5px radius.
8. **The infrastructure is real** — SQS/DLQ/SNS/CloudWatch, Kubernetes probes and HPA.
