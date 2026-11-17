# Settlement Guard Operations Runbook

## Service Architecture
Settlement Guard provides financial transaction settlement reconciliation, dual-entry verification, and outbox event streaming.

## Monitoring & Alerting
- Health endpoint: `GET /actuator/health`
- SLO: 99.99% availability, p95 latency < 25ms.
- Latency alert triggers if p95 exceeds 50ms over a 5-minute rolling window.

## Incident Response
1. Identify failing node or pod via Grafana / Prometheus dashboards.
2. Check logs for reconciliation drift or database deadlock exceptions.
3. Drain traffic from failing pod using Kubernetes service mesh.

## Rollback Procedure
If a production release encounters schema migration errors or critical reconciliation anomalies:
1. Identify the previous verified release tag (`git tag -l` or Docker registry tag).
2. Execute Kubernetes rollback:
   ```bash
   kubectl rollout undo deployment/settlement-guard -n production
   ```
3. Verify pod readiness and health endpoints:
   ```bash
   bash scripts/smoke.sh
   ```
4. If database rollback is required, apply the inverse Flyway migration script from `src/main/resources/db/migration`.
5. Post-mortem review: Log event timelines and schedule blameless retrospective.
